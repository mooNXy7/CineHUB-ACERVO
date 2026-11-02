#!/usr/bin/env python3
"""Read-only audit of missing TMDB metadata by the exact stable offsets used by enrichment."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
FIELDS = ("poster_url", "year", "genres", "overview")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def safe_path(root: Path, relative: str) -> Path:
    base = root.resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"Catalog path escapes repository root: {relative}")
    return path


def missing_fields(record: dict) -> list[str]:
    return [field for field in FIELDS
            if record.get(field) is None or record.get(field) == "" or record.get(field) == []]


def build_report(root: Path = ROOT, window_size: int = 5000) -> dict:
    if window_size < 1 or window_size > 5000:
        raise ValueError("window_size must be between 1 and 5000")
    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {})
    shard_cache: dict[str, dict[str, dict]] = {}
    windows: dict[int, dict] = defaultdict(lambda: {
        "offset": 0, "eligible_records": 0, "records_with_missing_metadata": 0,
        "complete_records": 0, "identity_mismatches": 0,
        "missing_field_counts": {field: 0 for field in FIELDS},
        "categories": {},
    })
    global_counts = {
        "eligible_records": 0, "records_with_missing_metadata": 0,
        "complete_records": 0, "identity_mismatches": 0,
        "missing_field_counts": {field: 0 for field in FIELDS},
    }
    for section in SECTIONS:
        if section not in categories:
            continue
        info = categories[section]
        index_path = info.get("index_path", f"catalog/vod/index/{section}.json")
        entries = load_json(safe_path(root, index_path))
        if not isinstance(entries, list):
            raise ValueError(f"VOD index for {section} is not a list")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tmdb_id = str(entry.get("tmdb_id") or "").strip()
            if not tmdb_id.isdigit():
                continue
            position = global_counts["eligible_records"]
            window_no = position // window_size
            bucket = windows[window_no]
            bucket["offset"] = window_no * window_size
            bucket["eligible_records"] += 1
            cat = bucket["categories"].setdefault(section, {
                "eligible_records": 0, "records_with_missing_metadata": 0,
                "complete_records": 0, "identity_mismatches": 0,
                "missing_field_counts": {field: 0 for field in FIELDS},
            })
            cat["eligible_records"] += 1
            global_counts["eligible_records"] += 1

            detail_path = str(entry.get("detail_path") or "")
            detail_id = str(entry.get("id") or "")
            if not detail_path or not detail_id:
                bucket["identity_mismatches"] += 1
                cat["identity_mismatches"] += 1
                global_counts["identity_mismatches"] += 1
                continue
            resolved = safe_path(root, detail_path)
            key = resolved.as_posix()
            if key not in shard_cache:
                shard = load_json(resolved)
                if not isinstance(shard, list):
                    raise ValueError(f"VOD detail shard is not a list: {detail_path}")
                shard_cache[key] = {
                    str(item.get("id")): item for item in shard
                    if isinstance(item, dict) and item.get("id")
                }
            record = shard_cache[key].get(detail_id)
            if not isinstance(record, dict) or str(record.get("tmdb_id") or "").strip() != tmdb_id:
                bucket["identity_mismatches"] += 1
                cat["identity_mismatches"] += 1
                global_counts["identity_mismatches"] += 1
                continue
            missing = missing_fields(record)
            if not missing:
                bucket["complete_records"] += 1
                cat["complete_records"] += 1
                global_counts["complete_records"] += 1
                continue
            bucket["records_with_missing_metadata"] += 1
            cat["records_with_missing_metadata"] += 1
            global_counts["records_with_missing_metadata"] += 1
            for field in missing:
                bucket["missing_field_counts"][field] += 1
                cat["missing_field_counts"][field] += 1
                global_counts["missing_field_counts"][field] += 1

    ordered = [windows[key] for key in sorted(windows)]
    for item in ordered:
        item["categories"] = dict(sorted(item["categories"].items()))
    return {
        "schema_version": 1,
        "report_type": "vod_tmdb_metadata_window_audit",
        "read_only": True,
        "network_accessed": False,
        "catalog_mutated": False,
        "window_size": window_size,
        "offset_semantics": "stable position among index entries with numeric tmdb_id, in movies/series/anime/doramas order",
        "summary": global_counts,
        "windows": ordered,
        "notes": [
            "This report uses the same eligible-record sequence and offset semantics as enrich_vod_metadata.py.",
            "A missing field count is not a guarantee that TMDB can safely supply it; provider identity checks still apply.",
            "Identity mismatches are excluded from automatic enrichment and require separate review.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--window-size", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/vod-metadata-window-audit.json")
    args = parser.parse_args()
    report = build_report(args.root, args.window_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"],
                      "windows": [{k: v for k, v in item.items() if k != "categories"}
                                  for item in report["windows"]],
                      "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
