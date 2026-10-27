#!/usr/bin/env python3
"""Summarize an isolated reference-import preview without exposing stream URLs or titles."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
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


def normalize_title(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"\b(?:4k|uhd|fhd|hd|1080p|720p|sd)\b", " ", value, flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


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
    duplicate_titles: dict[str, Any] = {}
    duplicate_title_examples: dict[str, list[dict[str, Any]]] = {}
    records_by_section: dict[str, list[dict[str, Any]]] = {}
    for section in SECTIONS:
        info = category_manifest.get(section, {}) if isinstance(category_manifest, dict) else {}
        relative = info.get("index_path", f"catalog/vod/index/{section}.json")
        records = read_json(safe_path(root, relative), [])
        if not isinstance(records, list):
            raise ValueError(f"VOD index for {section} is not a list")
        category_counts[section] = len(records)
        records_by_section[section] = [record for record in records if isinstance(record, dict)]
        title_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if not isinstance(record, dict):
                continue
            title_key = normalize_title(record.get("title"))
            if title_key:
                title_groups[title_key].append(record)
            for field in MISSING_FIELDS:
                value = record.get(field)
                if value is None or value == "" or value == []:
                    missing[f"missing_{field}"] += 1
            totals["source_count"] += int(record.get("source_count") or 0)
            totals["provider_ref_count"] += int(record.get("provider_ref_count") or 0)
        duplicate_groups = [(key, group) for key, group in title_groups.items() if len(group) > 1]
        duplicate_titles[section] = {
            "groups": len(duplicate_groups),
            "extra_records": sum(len(group) - 1 for _, group in duplicate_groups),
        }
        duplicate_title_examples[section] = [
            {
                "normalized_title": key,
                "items": [
                    {
                        "id": str(item.get("id") or ""),
                        "title": str(item.get("title") or ""),
                        "year": str(item.get("year") or ""),
                        "tmdb_id": str(item.get("tmdb_id") or ""),
                    }
                    for item in group[:5]
                ],
                "count": len(group),
            }
            for key, group in sorted(duplicate_groups, key=lambda pair: pair[0])[:25]
        ]

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
        "vod_duplicate_titles_by_category": duplicate_titles,
        "vod_duplicate_title_examples": duplicate_title_examples,
        "vod_record_ids_by_category": {
            section: [str(item.get("id") or "") for item in records]
            for section, records in records_by_section.items()
        },
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
    delta = {
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
        "vod_duplicate_titles_by_category": {
            section: {
                field: after["vod_duplicate_titles_by_category"][section][field]
                - before["vod_duplicate_titles_by_category"][section][field]
                for field in ("groups", "extra_records")
            }
            for section in SECTIONS
        },
    }
    new_record_missing_metadata: dict[str, Any] = {}
    after_manifest = read_json(after_root / "catalog/vod/index.json", {})
    after_categories = after_manifest.get("categories", {}) if isinstance(after_manifest, dict) else {}
    for section in SECTIONS:
        before_ids = set(before.get("vod_record_ids_by_category", {}).get(section, []))
        after_ids = set(after.get("vod_record_ids_by_category", {}).get(section, []))
        new_ids = {ident for ident in after_ids if ident and ident not in before_ids}
        relative = after_categories.get(section, {}).get("index_path", f"catalog/vod/index/{section}.json")
        after_records = read_json(safe_path(after_root, relative), [])
        missing_counts = Counter()
        examples = []
        records_with_missing = 0
        for item in after_records if isinstance(after_records, list) else []:
            if not isinstance(item, dict) or str(item.get("id") or "") not in new_ids:
                continue
            missing_fields = [field for field in MISSING_FIELDS if item.get(field) is None or item.get(field) == "" or item.get(field) == []]
            if missing_fields:
                records_with_missing += 1
            for field in missing_fields:
                missing_counts[field] += 1
            if missing_fields and len(examples) < 50:
                examples.append({
                    "id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "year": str(item.get("year") or ""),
                    "missing_fields": missing_fields,
                    "has_external_id": any(item.get(field) for field in ("tmdb_id", "imdb_id", "tvdb_id", "mal_id", "anilist_id")),
                })
        new_record_missing_metadata[section] = {
            "new_record_count": len(new_ids),
            "records_with_missing_metadata": records_with_missing,
            "missing_field_counts": dict(missing_counts),
            "examples_included": len(examples),
            "examples_truncated": records_with_missing > len(examples),
            "examples": examples,
        }
    blocking_reasons = []
    for section, change in delta["vod_counts"].items():
        if change < 0:
            blocking_reasons.append(f"VOD count decreased for {section}: {change}")
    for field, change in delta["vod_missing_metadata"].items():
        if change > 0:
            blocking_reasons.append(f"Missing VOD metadata increased for {field}: +{change}")
    for section, changes in delta["vod_duplicate_titles_by_category"].items():
        if changes["groups"] > 0:
            blocking_reasons.append(f"Normalized duplicate-title groups increased for {section}: +{changes['groups']}")
    for label, counts in (("channels", delta["channels"]), ("radios", delta["radios"])):
        if counts.get(label, 0) < 0:
            blocking_reasons.append(f"{label.capitalize()} count decreased: {counts[label]}")
    for field, change in delta["vod_source_references_in_index"].items():
        if change < 0:
            blocking_reasons.append(f"VOD reference count decreased for {field}: {change}")
    return {
        "schema_version": 1,
        "report_type": "isolated_reference_import_preview",
        "read_only_from_published_repository": True,
        "catalog_published": False,
        "network_sources_in_report": False,
        "review_gate": {
            "status": "blocked_pending_review" if blocking_reasons else "manual_approval_required",
            "automatic_approval_allowed": False,
            "blocking_reasons": blocking_reasons,
        },
        "before": before,
        "after_preview": after,
        "delta": delta,
        "duplicate_title_examples": {
            "before": before.get("vod_duplicate_title_examples", {}),
            "after_preview": after.get("vod_duplicate_title_examples", {}),
        },
        "new_records_missing_metadata": new_record_missing_metadata,
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
