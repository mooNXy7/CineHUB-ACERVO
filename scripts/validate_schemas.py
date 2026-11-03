#!/usr/bin/env python3
"""Validate versioned JSON Schemas and candidate documents with bounded memory."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import ijson
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = sorted((ROOT / "schemas").rglob("*.schema.json"))
CANDIDATE_SCHEMAS = {
    "vod.json": "vod/v1.schema.json",
    "channels.json": "channels/v1.schema.json",
    "radios.json": "radios/v1.schema.json",
    "logos.json": "logos/v1.schema.json",
    "sources.json": "sources/v1.schema.json",
    "epg-sources.json": "epg/sources-v1.schema.json",
    "epg-mappings.json": "epg/mappings-v1.schema.json",
    "epg-channels.json": "epg/channels-v1.schema.json",
    "epg-programmes.json": "epg/programmes-v1.schema.json",
}


def iter_records(path: Path):
    with path.open("rb") as stream:
        yield from ijson.items(stream, "records.item")


def iter_quarantine(path: Path):
    with path.open("rb") as stream:
        yield from ijson.items(stream, "quarantine.item")


def read_candidate_header(path: Path) -> dict:
    header = {"keys": set(), "schema_version": None, "domain": None,
              "records_array": False, "quarantine_array": False}
    with path.open("rb") as stream:
        for prefix, event, value in ijson.parse(stream):
            if prefix == "" and event == "map_key":
                header["keys"].add(value)
            elif prefix == "schema_version" and event in {"number", "integer"}:
                header["schema_version"] = value
            elif prefix == "domain" and event == "string":
                header["domain"] = value
            elif prefix == "records" and event == "start_array":
                header["records_array"] = True
            elif prefix == "quarantine" and event == "start_array":
                header["quarantine_array"] = True
    return header


def validate_candidate_document(path: Path, schema: dict, registry: Registry) -> list[str]:
    errors = []
    header = read_candidate_header(path)
    required = set(schema.get("required", []))
    missing = sorted(required - header["keys"])
    if missing:
        errors.append("missing top-level fields: " + ", ".join(missing))
        return errors
    if not header["records_array"]:
        errors.append("records must be an array")
    if not header["quarantine_array"]:
        errors.append("quarantine must be an array")
    header_document = {
        "schema_version": header["schema_version"], "domain": header["domain"],
        "records": [], "quarantine": [],
    }
    header_validator = Draft202012Validator(schema, format_checker=FormatChecker(), registry=registry)
    for error in header_validator.iter_errors(header_document):
        if error.absolute_path and error.absolute_path[0] not in {"records", "quarantine"}:
            errors.append("header: " + error.message)

    root_validator = Draft202012Validator(schema, format_checker=FormatChecker(), registry=registry)
    record_schema = schema["properties"]["records"]["items"]
    # evolve() retains the root schema's resolver/base URI for relative $refs.
    record_validator = root_validator.evolve(schema=record_schema)
    for index, record in enumerate(iter_records(path)):
        for error in record_validator.iter_errors(record):
            location = "/".join(str(part) for part in error.absolute_path)
            errors.append(f"records[{index}]/{location}: {error.message}")

    quarantine_schema = schema["properties"]["quarantine"]["items"]
    quarantine_validator = root_validator.evolve(schema=quarantine_schema)
    for index, record in enumerate(iter_quarantine(path)):
        for error in quarantine_validator.iter_errors(record):
            errors.append(f"quarantine[{index}]: {error.message}")
    return errors


def validate_candidate_integrity(candidate_dir: Path) -> tuple[list[str], dict]:
    """Check cross-document identity and relationship invariants without loading VOD in memory."""
    errors = []
    ids_by_file = {}
    entity_count = {"channels": 0, "radios": 0, "vod": 0}
    stream_count = 0
    quarantine_count = 0

    for filename, label in (("channels.json", "channels"), ("radios.json", "radios"), ("vod.json", "vod")):
        path = candidate_dir / filename
        seen = set()
        for index, record in enumerate(iter_records(path)):
            entity_count[label] += 1
            ident = str(record.get("id") or "")
            if not ident:
                errors.append(f"{filename}[{index}]: missing canonical id")
            elif ident in seen:
                errors.append(f"{filename}[{index}]: duplicate id {ident}")
            seen.add(ident)
            provenance = record.get("provenance", [])
            if not provenance:
                errors.append(f"{filename}[{index}]: missing provenance")
            for pindex, item in enumerate(provenance):
                digest = str(item.get("input_sha256") or "")
                if not item.get("source_id") or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    errors.append(f"{filename}[{index}].provenance[{pindex}]: invalid source/hash")
            variants = list(record.get("streams", [])) + list(record.get("sources", []))
            for season in record.get("seasons", []) if isinstance(record.get("seasons"), list) else []:
                for episode in season.get("episodes", []) if isinstance(season, dict) and isinstance(season.get("episodes"), list) else []:
                    variants.extend(episode.get("sources", []) if isinstance(episode, dict) else [])
            seen_streams = set()
            for variant in variants:
                stream_count += 1
                if str(variant.get("entity_id") or "") != ident:
                    errors.append(f"{filename}:{ident}: stream entity_id does not match owner")
                stream_id = str(variant.get("id") or "")
                if stream_id and stream_id in seen_streams:
                    errors.append(f"{filename}:{ident}: duplicate stream variant id {stream_id}")
                seen_streams.add(stream_id)
        ids_by_file[filename] = seen

    channel_ids = ids_by_file.get("channels.json", set())
    radio_ids = ids_by_file.get("radios.json", set())
    vod_ids = ids_by_file.get("vod.json", set())

    logo_records = list(iter_records(candidate_dir / "logos.json"))
    for asset in logo_records:
        entity_id = str(asset.get("entity_id") or "")
        kind = str(asset.get("kind") or "")
        if kind == "channel_logo" and entity_id not in channel_ids:
            errors.append(f"logos.json: orphan channel logo {entity_id}")
        elif kind == "radio_logo" and entity_id not in radio_ids:
            errors.append(f"logos.json: orphan radio logo {entity_id}")
        elif kind in {"poster", "backdrop"} and entity_id not in vod_ids:
            errors.append(f"logos.json: orphan VOD asset {entity_id}")
        elif kind not in {"channel_logo", "radio_logo", "poster", "backdrop"}:
            errors.append(f"logos.json: unsupported logo kind {kind}")

    matched_mappings = unmatched_mappings = ambiguous_mappings = 0
    for mapping in iter_records(candidate_dir / "epg-mappings.json"):
        status = mapping.get("match_status", "unresolved")
        if status == "matched":
            matched_mappings += 1
            if str(mapping.get("channel_id") or "") not in channel_ids:
                errors.append("epg-mappings.json: matched mapping points to missing channel")
        elif status == "ambiguous":
            ambiguous_mappings += 1
            if mapping.get("channel_id"):
                errors.append("epg-mappings.json: ambiguous mapping must not assign channel_id")
        else:
            unmatched_mappings += 1

    epg_channel_keys = {
        (str(item.get("source_id") or ""), str(item.get("provider_channel_id") or item.get("id") or ""))
        for item in iter_records(candidate_dir / "epg-channels.json")
    }
    epg_channel_count = len(epg_channel_keys)
    epg_programme_count = 0
    for programme in iter_records(candidate_dir / "epg-programmes.json"):
        epg_programme_count += 1
        key = (str(programme.get("source_id") or ""), str(programme.get("epg_channel_id") or ""))
        if epg_channel_keys and key not in epg_channel_keys:
            errors.append(f"epg-programmes.json: programme references missing EPG channel {key}")

    for filename in CANDIDATE_SCHEMAS:
        quarantine_count += sum(1 for _ in iter_quarantine(candidate_dir / filename))

    metrics = {
        "entities": entity_count,
        "streams_and_episode_variants": stream_count,
        "logos_associated": len(logo_records),
        "epg_channels": epg_channel_count,
        "epg_programmes": epg_programme_count,
        "epg_mappings": {"matched": matched_mappings, "unmatched": unmatched_mappings,
                         "ambiguous": ambiguous_mappings},
        "quarantine_records": quarantine_count,
    }
    return errors, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path)
    args = parser.parse_args()
    errors = []
    schemas = {}
    for path in SCHEMA_FILES:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            schemas[path.relative_to(ROOT / "schemas").as_posix()] = schema
        except Exception as exc:
            errors.append(str(path.relative_to(ROOT)) + ": " + str(exc))
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    if args.candidate_dir:
        for filename, schema_name in CANDIDATE_SCHEMAS.items():
            path = args.candidate_dir / filename
            if not path.exists():
                errors.append("candidate missing: " + filename)
                continue
            try:
                errors.extend(filename + ": " + error for error in
                              validate_candidate_document(path, schemas[schema_name], registry))
            except Exception as exc:
                errors.append(filename + ": " + str(exc))
        try:
            integrity_errors, integrity_metrics = validate_candidate_integrity(args.candidate_dir)
            errors.extend("integrity: " + item for item in integrity_errors)
            if not integrity_errors:
                print("OK: candidate integrity " + json.dumps(integrity_metrics, ensure_ascii=False, sort_keys=True))
        except Exception as exc:
            errors.append("candidate integrity: " + str(exc))
    if errors:
        print("\\n".join("ERROR: " + error for error in errors))
        raise SystemExit(1)
    print("OK: " + str(len(SCHEMA_FILES)) + " JSON Schemas validated" +
          ("; candidate documents valid" if args.candidate_dir else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
