#!/usr/bin/env python3
"""Build V2 canonical candidates from the current local catalog without mutating it or using the network."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

# Direct script execution sets sys.path[0] to scripts/, not the repository root.
# Keep checkout-local imports working without requiring network or editable installs.
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from datetime import datetime, timezone

from acervo_v2.importers import (
    apply_radio_reference_recovery, parse_channels_json, parse_epg_channel_index, parse_epg_mapping,
    parse_epg_sources, parse_logo_references, parse_source_registry, iter_vod_catalog,
    parse_m3u, parse_radios_json, parse_vod_catalog, normalize_name,
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def merge_channel_candidates(existing: list, incoming: list) -> list:
    by_id = {item["id"]: item for item in existing}
    for item in incoming:
        target = by_id.get(item["id"])
        if target is None:
            existing.append(item)
            by_id[item["id"]] = item
            continue
        known = {(source["url"], source.get("audio"), source.get("source_id")) for source in target.get("streams", [])}
        for stream in item.get("streams", []):
            key = (stream["url"], stream.get("audio"), stream.get("source_id"))
            if key not in known:
                target.setdefault("streams", []).append(stream)
                known.add(key)
        target.setdefault("provenance", []).extend(
            p for p in item.get("provenance", []) if p not in target.get("provenance", [])
        )
    return existing


def write_vod_document(path: Path, records, quarantine: list) -> tuple[str, int, int]:
    """Write a potentially large VOD document incrementally and atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    digest = hashlib.sha256()
    count = 0
    try:
        with os.fdopen(fd, "wb") as stream:
            def emit(value: str):
                data = value.encode("utf-8")
                stream.write(data)
                digest.update(data)

            emit('{"schema_version":1,"domain":"vod","records":[')
            for record in records:
                if count:
                    emit(",")
                emit(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                count += 1
            emit('],"quarantine":')
            emit(json.dumps(quarantine, ensure_ascii=False, separators=(",", ":")))
            emit("}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return digest.hexdigest(), count, len(quarantine)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("staging/phase-b/candidate"))
    parser.add_argument("--m3u", type=Path, default=Path("sources/m3u/public-brazil.m3u"))
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()

    channels_doc = read_json(root / "catalog/channels/channels.json")
    radios_doc = read_json(root / "catalog/radios/radios.json")
    channels, q_channels = parse_channels_json(channels_doc)
    radios, q_radios = parse_radios_json(radios_doc)
    radio_recovery_path = root / "sources/reference/radio-recovery.json"
    radio_recovery_doc = read_json(radio_recovery_path) if radio_recovery_path.exists() else {}
    radio_recovery_report = apply_radio_reference_recovery(radios, q_radios, radio_recovery_doc)
    if args.m3u:
        m3u_path = args.m3u if args.m3u.is_absolute() else root / args.m3u
        if m3u_path.exists():
            incoming, rejected = parse_m3u(m3u_path.read_text(encoding="utf-8-sig"),
                                           "cinehub-curated-m3u", m3u_path.relative_to(root).as_posix())
            channels = merge_channel_candidates(channels, incoming)
            q_channels.extend(rejected)

    q_vod = []
    vod_identity_report = {}
    vod_identity_override_path = root / "sources/reference/vod-identity-overrides.json"
    vod_identity_override_doc = read_json(vod_identity_override_path) if vod_identity_override_path.exists() else {}
    vod_records = iter_vod_catalog(
        root, "catalog-existing", q_vod, vod_identity_report,
        identity_overrides=vod_identity_override_doc,
    )
    epg_sources_doc = read_json(root / "catalog/epg/sources.json")
    epg_map_doc = read_json(root / "catalog/epg/channel-map.json")
    epg_sources, q_epg_sources = parse_epg_sources(epg_sources_doc)
    for source in epg_sources:
        source["domain"] = "epg"
    epg_mappings, q_epg_map = parse_epg_mapping(epg_map_doc)
    epg_channel_index_path = root / "catalog/epg/xmltv-channels.json"
    if epg_channel_index_path.exists():
        epg_channels, q_epg_channels = parse_epg_channel_index(
            read_json(epg_channel_index_path), "catalog/epg/xmltv-channels.json")
    else:
        epg_channels, q_epg_channels = [], []
    source_priorities = {
        str(source["id"]): int(source.get("priority", 100))
        for source in epg_sources if source.get("id")
    }
    for epg_channel in epg_channels:
        epg_channel["source_priority"] = source_priorities.get(epg_channel.get("source_id"))
    # Attach legacy name-based EPG mappings to a CineHUB channel only when the
    # normalized name resolves uniquely. Ambiguous/unmatched mappings remain visible.
    channel_names = {}
    for channel in channels:
        for name in [channel.get("name"), *(channel.get("aliases") or [])]:
            key = normalize_name(name)
            if key:
                channel_names.setdefault(key, set()).add(channel["id"])
    for mapping in epg_mappings:
        key = normalize_name(mapping.get("channel_name"))
        matches = sorted(channel_names.get(key, set()))
        mapping["candidate_channel_ids"] = matches
        mapping["match_status"] = "matched" if len(matches) == 1 else ("ambiguous" if matches else "unmatched")
        if len(matches) == 1:
            mapping["channel_id"] = matches[0]
    source_registry_doc = read_json(root / "sources/sources.json")
    source_registry, q_source_registry = parse_source_registry(source_registry_doc)
    reference_source_records = [
        {
            "id": "reference-radio-catalog", "domain": "radios",
            "name": "Radio reference recovery snapshot", "format": "json-reference",
            "url": None, "priority": 0, "enabled": False, "license": None,
            "match_strategy": "exact_stream_url_reference",
            "raw": radio_recovery_doc.get("source", {}),
        },
        {
            "id": "reference-vod-identity", "domain": "vod",
            "name": "VOD identity override snapshot", "format": "json-reference",
            "url": None, "priority": 0, "enabled": False, "license": None,
            "match_strategy": "explicit_tmdb_identity_override",
            "raw": vod_identity_override_doc.get("source", {}),
        },
    ]
    known_source_ids = {item.get("id") for item in source_registry}
    for reference_source in reference_source_records:
        if reference_source["id"] not in known_source_ids and (
            (reference_source["id"] == "reference-radio-catalog" and radio_recovery_doc)
            or (reference_source["id"] == "reference-vod-identity" and vod_identity_override_doc)
        ):
            source_registry.append(reference_source)
            known_source_ids.add(reference_source["id"])
    logos, q_logos = parse_logo_references(channels, radios)

    docs = {
        "channels.json": {"schema_version": 1, "domain": "channels", "records": channels, "quarantine": q_channels},
        "radios.json": {"schema_version": 1, "domain": "radios", "records": radios, "quarantine": q_radios},
        "logos.json": {"schema_version": 1, "domain": "logos", "records": logos, "quarantine": q_logos},
        "sources.json": {"schema_version": 1, "domain": "sources", "records": source_registry, "quarantine": q_source_registry},
        "epg-sources.json": {"schema_version": 1, "domain": "epg-sources", "records": epg_sources, "quarantine": q_epg_sources},
        "epg-mappings.json": {"schema_version": 1, "domain": "epg-mappings", "records": epg_mappings, "quarantine": q_epg_map},
        "epg-channels.json": {"schema_version": 1, "domain": "epg-channels", "records": epg_channels, "quarantine": q_epg_channels},
        "epg-programmes.json": {"schema_version": 1, "domain": "epg-programmes", "records": [], "quarantine": []},
    }
    generated_at = (datetime.fromtimestamp(int(os.environ["SOURCE_DATE_EPOCH"]), timezone.utc)
                    .replace(microsecond=0).isoformat().replace("+00:00", "Z")
                    if os.environ.get("SOURCE_DATE_EPOCH", "").isdigit() else None)
    file_entries = {}
    vod_digest, vod_count, vod_quarantine_count = write_vod_document(
        output / "vod.json", vod_records, q_vod)
    file_entries["vod.json"] = {"sha256": vod_digest, "records": vod_count,
                                "quarantine": vod_quarantine_count}
    for name, document in docs.items():
        digest = write_json(output / name, document)
        file_entries[name] = {"sha256": digest, "records": len(document["records"]),
                              "quarantine": len(document["quarantine"])}
    radio_quarantine_reasons = dict(sorted(Counter(
        str(item.get("reason") or "unknown") for item in q_radios
    ).items()))
    radio_records_without_streams = sum(not item.get("streams") for item in radios)
    epg_channels_by_source = Counter(str(item.get("source_id") or "") for item in epg_channels)
    epg_provider_id_sources = defaultdict(set)
    epg_display_name_sources = defaultdict(set)
    for item in epg_channels:
        provider_id = str(item.get("provider_channel_id") or "")
        if provider_id:
            epg_provider_id_sources[provider_id].add(str(item.get("source_id") or ""))
        for display_name in item.get("display_names", []):
            key = normalize_name(display_name)
            if key:
                epg_display_name_sources[key].add(str(item.get("source_id") or ""))
    epg_mapping_statuses = dict(sorted(Counter(
        str(item.get("match_status") or "unclassified") for item in epg_mappings
    ).items()))
    epg_mapping_types = dict(sorted(Counter(
        str(item.get("mapping_type") or "unknown") for item in epg_mappings
    ).items()))
    logo_kind_counts = dict(sorted(Counter(str(item.get("kind") or "unknown") for item in logos).items()))
    logo_status_counts = dict(sorted(Counter(str(item.get("status") or "unknown") for item in logos).items()))
    logo_scheme_counts = dict(sorted(Counter(
        urlsplit(str(item.get("url") or "")).scheme.lower()
        for item in logos if item.get("url")
    ).items()))
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".avif", ".bmp"}
    logo_root = root / "catalog/logos"
    local_logo_files = [
        path for path in logo_root.rglob("*")
        if path.is_file() and path.suffix.lower() in image_suffixes
    ] if logo_root.exists() else []
    quality_audit = {
        "radios": {
            "records": len(radios),
            "records_without_valid_streams": radio_records_without_streams,
            "quarantine_count": len(q_radios),
            "quarantine_reason_counts": radio_quarantine_reasons,
            "quarantine_items_with_provenance": sum(bool(item.get("provenance")) for item in q_radios),
            "quarantine_items_with_resolution": sum(bool(item.get("resolution")) for item in q_radios),
            "reference_recovery": radio_recovery_report,
        },
        "epg": {
            "sources": [
                {
                    "id": source.get("id"),
                    "format": source.get("format"),
                    "priority": source.get("priority"),
                    "indexed_channels": epg_channels_by_source.get(str(source.get("id") or ""), 0),
                }
                for source in sorted(epg_sources, key=lambda item: (int(item.get("priority", 100)), str(item.get("id") or "")))
            ],
            "channel_records": len(epg_channels),
            "unique_source_provider_id_pairs": len({
                (str(item.get("source_id") or ""), str(item.get("provider_channel_id") or ""))
                for item in epg_channels
            }),
            "provider_ids_reused_across_feeds": sum(
                1 for source_ids in epg_provider_id_sources.values() if len(source_ids) > 1
            ),
            "normalized_display_names_reused_across_feeds": sum(
                1 for source_ids in epg_display_name_sources.values() if len(source_ids) > 1
            ),
            "mappings": {
                "total": len(epg_mappings),
                "status_counts": epg_mapping_statuses,
                "type_counts": epg_mapping_types,
                "ambiguous": [
                    {
                        "id": item.get("id"),
                        "channel_name": item.get("channel_name"),
                        "mapping_type": item.get("mapping_type"),
                        "value": item.get("value"),
                        "candidate_channel_ids": item.get("candidate_channel_ids", []),
                    }
                    for item in epg_mappings if item.get("match_status") == "ambiguous"
                ],
            },
            "programme_records": 0,
            "local_programme_payload_present": False,
        },
        "logos": {
            "logical_associations": len(logos),
            "kind_counts": logo_kind_counts,
            "status_counts": logo_status_counts,
            "external_url_count": sum(bool(item.get("url")) for item in logos),
            "url_scheme_counts": logo_scheme_counts,
            "local_image_files": len(local_logo_files),
            "mime_type_present_count": sum(bool(item.get("mime_type")) for item in logos),
            "mime_verified_count": sum(bool(item.get("mime_type")) and item.get("mime_verified") is True for item in logos),
            "content_hash_present_count": sum(bool(item.get("content_sha256")) for item in logos),
            "content_verified_count": sum(item.get("content_verified") is True and bool(item.get("content_sha256")) for item in logos),
            "license_documented_count": sum(bool(item.get("license")) for item in logos),
        },
    }
    reference_inputs = []
    for reference_path in (radio_recovery_path, vod_identity_override_path):
        if reference_path.exists():
            reference_document = read_json(reference_path)
            reference_source = reference_document.get("source", {}) if isinstance(reference_document, dict) else {}
            reference_inputs.append({
                "path": reference_path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                "source_id": reference_source.get("source_id"),
                "repository": reference_source.get("repository"),
                "commit": reference_source.get("commit"),
                "source_paths": (
                    [reference_source.get("path")] if reference_source.get("path")
                    else [item.get("path") for item in reference_source.get("files", []) if item.get("path")]
                ),
            })
    reference_inputs.sort(key=lambda item: item["path"])
    report = {
        "schema_version": 1, "report_type": "phase_b_candidate_build",
        "generated_at": generated_at, "catalog_mutated": False,
        "reference_network_used": False, "active_catalogs_modified": False,
        "domains": file_entries,
        "vod_identity": vod_identity_report,
        "quality_audit": quality_audit,
        "reference_inputs": reference_inputs,
        "notes": [
            "Candidates are isolated from catalog/ and sources/; no active record was written.",
            "EPG channels are normalized from the repository-owned xmltv-channels.json index; no local XMLTV programme payload is present, so programme records remain empty until an authorized local feed payload is ingested.",
            "Source registry candidates are normalized from sources/sources.json; external source adapters remain optional.",
            "Pinned radio and VOD reference snapshots are local build inputs only; no external network calls or active catalog mutations occur.",
            "Logo records reference external URLs; local image bytes, MIME and license remain unverified.",
        ],
    }
    report_hash = write_json(output / "report.json", report)
    manifest = {"schema_version": 1, "generated_at": generated_at,
                "base_ref": __import__("os").environ.get("GITHUB_SHA"),
                "files": file_entries, "report_sha256": report_hash,
                "reference_inputs": reference_inputs}
    write_json(output / "manifest.json", manifest)
    identity_log_summary = {
        key: value for key, value in vod_identity_report.items()
        if key not in {"consolidations", "legacy_id_conflicts"}
    }
    identity_log_summary["consolidation_details"] = len(vod_identity_report.get("consolidations", []))
    identity_log_summary["legacy_id_conflict_details"] = len(vod_identity_report.get("legacy_id_conflicts", []))
    quality_log_summary = {
        "radio_quarantine_count": quality_audit["radios"]["quarantine_count"],
        "radio_records_without_valid_streams": quality_audit["radios"]["records_without_valid_streams"],
        "radio_reference_recovered": radio_recovery_report.get("applied_records", 0),
        "vod_identity_override_references": vod_identity_report.get("identity_override_index_references", 0),
        "epg_channel_records": quality_audit["epg"]["channel_records"],
        "epg_mapping_status_counts": quality_audit["epg"]["mappings"]["status_counts"],
        "logo_associations": quality_audit["logos"]["logical_associations"],
        "local_logo_files": quality_audit["logos"]["local_image_files"],
    }
    print(json.dumps({"output": str(output), "domains": file_entries,
                      "vod_identity": identity_log_summary,
                      "quality_audit": quality_log_summary,
                      "active_catalogs_modified": False, "reference_network_used": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
