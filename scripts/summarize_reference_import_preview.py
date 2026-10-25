#!/usr/bin/env python3
"""Summarize an isolated reference-import preview without exposing stream URLs or titles."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
MISSING_FIELDS = ("poster_url", "year", "genres")


def read_json(path: Path, fallback: Any = None) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError):
        return fallback


def safe_path(root: Path, relative: str) -> Path:
    base = root.resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"Catalog index path escapes repository root: {relative}")
    return path


def snapshot(root: Path) -> dict[str, Any]:
    channels_doc = read_json(root / "catalog/channels/channels.json", {})
    radios_doc = read_json(root / "catalog/radios/radios.json", {})
    manifest = read_json(root / "catalog/vod/index.json", {})
    channels = channels_doc.get("channels", []) if isinstance(channels_doc, dict) else []
    radios = radios_doc.get("radios", []) if isinstance(radios_doc, dict) else []
    category_manifest = manifest.get("categories", {}) if isinstance(manifest, dict) else {}

    category_counts: dict[str, Any] = {}
    missing = Counter()
    totals = Counter()
    for section in SECTIONS:
        info = category_manifest.get(section, {}) if isinstance(category_manifest, dict) else {}
        relative = info.get("index_path", f"catalog/vod/index/{section}.json")
        records = read_json(safe_path(root, relative), [])
        if not isinstance(records, list):
            raise ValueError(f"VOD index for {section} is not a list")
        category_counts[section] = len(records)
        for record in records:
            if not isinstance(record, dict):
                continue
            for field in MISSING_FIELDS:
                value = record.get(field)
                if value is None or value == "" or value == []:
                    missing[f"missing_{field}"] += 1
            totals["source_count"] += int(record.get("source_count") or 0)
            totals["provider_ref_count"] += int(record.get("provider_ref_count") or 0)

    channel_counts = Counter()
    for item in channels if isinstance(channels, list) else []:
        if not isinstance(item, dict):
            continue
        channel_counts["channels"] += 1
        channel_counts["channels_with_source_list"] += bool(
            any(isinstance(source, dict) and source.get("url") for source in item.get("sources", []))
        )
        channel_counts["channels_with_epg_id"] += bool(item.get("epg_id"))
        channel_counts["channels_with_logo"] += bool(item.get("logo_url"))

    radio_counts = Counter()
    for item in radios if isinstance(radios, list) else []:
        if not isinstance(item, dict):
            continue
        radio_counts["radios"] += 1
        radio_counts["radios_with_stream"] += bool(item.get("stream_url"))
        radio_counts["radios_with_logo"] += bool(item.get("logo_url"))
        radio_counts["radios_with_genre"] += bool(item.get("genre"))

    return {
        "vod_counts": category_counts,
        "vod_total": sum(category_counts.values()),
        "vod_missing_metadata": {field: int(missing[f"missing_{field}"]) for field in MISSING_FIELDS},
        "vod_source_references_in_index": dict(totals),
        "channels": dict(channel_counts),
        "radios": dict(radio_counts),
    }


def build_summary(before_root: Path, after_root: Path, import_report_path: Path | None = None) -> dict[str, Any]:
    before = snapshot(before_root)
    after = snapshot(after_root)
    import_report = read_json(import_report_path, {}) if import_report_path else {}
    counters = import_report.get("counts", {}) if isinstance(import_report, dict) else {}
    safe_counters = {
        str(key): int(value)
        for key, value in counters.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    return {
        "schema_version": 1,
        "report_type": "isolated_reference_import_preview",
        "read_only_from_published_repository": True,
        "catalog_published": False,
        "network_sources_in_report": False,
        "before": before,
        "after_preview": after,
        "delta": {
            "vod_total": after["vod_total"] - before["vod_total"],
            "vod_counts": {
                section: after["vod_counts"][section] - before["vod_counts"][section]
                for section in SECTIONS
            },
            "vod_missing_metadata": {
                field: after["vod_missing_metadata"][field] - before["vod_missing_metadata"][field]
                for field in MISSING_FIELDS
            },
            "channels": {
                key: after["channels"].get(key, 0) - before["channels"].get(key, 0)
                for key in set(before["channels"]) | set(after["channels"])
            },
            "radios": {
                key: after["radios"].get(key, 0) - before["radios"].get(key, 0)
                for key in set(before["radios"]) | set(after["radios"])
            },
            "vod_source_references_in_index": {
                key: after["vod_source_references_in_index"].get(key, 0)
                - before["vod_source_references_in_index"].get(key, 0)
                for key in set(before["vod_source_references_in_index"]) | set(after["vod_source_references_in_index"])
            },
        },
        "import_counters": safe_counters,
        "notes": [
            "Preview ran in a detached temporary worktree; no catalog files were published or committed.",
            "Counts contain no titles, stream URLs, logos, credentials, or provider response bodies.",
            "Source references are counted from the published VOD indexes; this does not prove playback.",
            "A positive or negative metadata delta is a review signal; existing catalog records must not be removed solely because they are absent from a reference.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-root", type=Path, default=ROOT)
    parser.add_argument("--after-root", type=Path, required=True)
    parser.add_argument("--import-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_summary(args.before_root, args.after_root, args.import_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "vod_total_before": result["before"]["vod_total"],
        "vod_total_after_preview": result["after_preview"]["vod_total"],
        "vod_delta": result["delta"]["vod_total"],
        "catalog_published": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
