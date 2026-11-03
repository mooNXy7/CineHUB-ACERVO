#!/usr/bin/env python3
"""Build V2 canonical candidates from the current local catalog without mutating it or using the network."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

# Direct script execution sets sys.path[0] to scripts/, not the repository root.
# Keep checkout-local imports working without requiring network or editable installs.
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from datetime import datetime, timezone

from acervo_v2.importers import (
    parse_channels_json, parse_epg_channel_index, parse_epg_mapping, parse_epg_sources, parse_logo_references, parse_source_registry,
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
    if args.m3u:
        m3u_path = args.m3u if args.m3u.is_absolute() else root / args.m3u
        if m3u_path.exists():
            incoming, rejected = parse_m3u(m3u_path.read_text(encoding="utf-8-sig"),
                                           "cinehub-curated-m3u", m3u_path.relative_to(root).as_posix())
            channels = merge_channel_candidates(channels, incoming)
            q_channels.extend(rejected)

    vod, q_vod = parse_vod_catalog(root)
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
        mapping["match_status"] = "matched" if len(matches) == 1 else ("ambiguous" if matches else "unmatched")
        if len(matches) == 1:
            mapping["channel_id"] = matches[0]
    source_registry_doc = read_json(root / "sources/sources.json")
    source_registry, q_source_registry = parse_source_registry(source_registry_doc)
    logos, q_logos = parse_logo_references(channels, radios)

    docs = {
        "vod.json": {"schema_version": 1, "domain": "vod", "records": vod, "quarantine": q_vod},
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
    for name, document in docs.items():
        digest = write_json(output / name, document)
        file_entries[name] = {"sha256": digest, "records": len(document["records"]),
                              "quarantine": len(document["quarantine"])}
    report = {
        "schema_version": 1, "report_type": "phase_b_candidate_build",
        "generated_at": generated_at, "catalog_mutated": False,
        "reference_network_used": False, "active_catalogs_modified": False,
        "domains": file_entries,
        "notes": [
            "Candidates are isolated from catalog/ and sources/; no active record was written.",
            "EPG channels are normalized from the repository-owned xmltv-channels.json index; no local XMLTV programme payload is present, so programme records remain empty until an authorized local feed payload is ingested.",
            "Source registry candidates are normalized from sources/sources.json; external source adapters remain optional."
            "Logo records reference existing catalog URLs only; MIME and image bytes remain unverified.",
        ],
    }
    report_hash = write_json(output / "report.json", report)
    manifest = {"schema_version": 1, "generated_at": generated_at,
                "base_ref": __import__("os").environ.get("GITHUB_SHA"),
                "files": file_entries, "report_sha256": report_hash}
    write_json(output / "manifest.json", manifest)
    print(json.dumps({"output": str(output), "domains": file_entries,
                      "active_catalogs_modified": False, "reference_network_used": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
