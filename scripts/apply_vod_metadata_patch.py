#!/usr/bin/env python3
"""Apply only verified, missing-field VOD metadata proposals to index and detail shards."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
ALLOWED_FIELDS = {"poster_url", "year", "genres", "overview"}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def safe_path(root: Path, relative: str) -> Path:
    base = root.resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"Catalog path escapes repository root: {relative}")
    return path


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def validate_value(field: str, value: Any) -> bool:
    if field == "year":
        return isinstance(value, str) and bool(re.fullmatch(r"(?:19|20)\d{2}", value))
    if field == "poster_url":
        return isinstance(value, str) and value.startswith("/") and not value.startswith("//") and "?" not in value
    if field == "genres":
        return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value)
    if field == "overview":
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 12000
    return False


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def apply_patch(root: Path, patch_path: Path, output: Path) -> dict:
    report = load_json(patch_path)
    if report.get("report_type") != "review_only_tmdb_metadata_patch" or report.get("catalog_mutated") is not False:
        raise ValueError("Unexpected metadata patch format; refusing to apply.")
    patches = report.get("patches")
    if not isinstance(patches, list):
        raise ValueError("Patch list is missing or invalid.")

    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {})
    indexes: dict[str, list] = {}
    index_paths: dict[str, Path] = {}
    shards: dict[str, list] = {}
    shard_paths: dict[str, Path] = {}
    for section in SECTIONS:
        info = categories.get(section)
        if not isinstance(info, dict):
            continue
        index_path = safe_path(root, info.get("index_path", f"catalog/vod/index/{section}.json"))
        entries = load_json(index_path)
        if not isinstance(entries, list):
            raise ValueError(f"VOD index for {section} is not a list.")
        indexes[section] = entries
        index_paths[section] = index_path

    counts = {"patches_received": len(patches), "records_updated": 0, "fields_updated": 0,
              "identity_rejected": 0, "field_conflict": 0, "already_filled": 0}
    changed_indexes: set[str] = set()
    changed_shards: set[str] = set()

    for patch in patches:
        if not isinstance(patch, dict) or patch.get("section") not in indexes:
            counts["identity_rejected"] += 1
            continue
        if patch.get("confidence") != "exact_provider_id_and_title":
            counts["identity_rejected"] += 1
            continue
        section = patch["section"]
        record_id = str(patch.get("id") or "")
        tmdb_id = str(patch.get("tmdb_id") or "")
        title = str(patch.get("title") or "")
        matched_title = str(patch.get("matched_title") or "")
        if not record_id or not tmdb_id.isdigit() or not title or norm(title) != norm(matched_title):
            counts["identity_rejected"] += 1
            continue

        matching_indexes = [x for x in indexes[section] if isinstance(x, dict) and str(x.get("id") or "") == record_id]
        if len(matching_indexes) != 1:
            counts["identity_rejected"] += 1
            continue
        index_record = matching_indexes[0]
        if norm(index_record.get("title")) != norm(title):
            counts["identity_rejected"] += 1
            continue
        index_tmdb = str(index_record.get("tmdb_id") or "").strip()
        if index_tmdb and index_tmdb != tmdb_id:
            counts["identity_rejected"] += 1
            continue
        detail_rel = str(index_record.get("detail_path") or "")
        if not detail_rel:
            counts["identity_rejected"] += 1
            continue
        detail_path = safe_path(root, detail_rel)
        shard_key = detail_path.as_posix()
        if shard_key not in shards:
            shard = load_json(detail_path)
            if not isinstance(shard, list):
                raise ValueError(f"VOD detail shard is not a list: {detail_rel}")
            shards[shard_key] = shard
            shard_paths[shard_key] = detail_path
        matching_details = [x for x in shards[shard_key] if isinstance(x, dict) and str(x.get("id") or "") == record_id]
        if len(matching_details) != 1:
            counts["identity_rejected"] += 1
            continue
        detail_record = matching_details[0]
        if norm(detail_record.get("title")) != norm(title):
            counts["identity_rejected"] += 1
            continue
        detail_tmdb = str(detail_record.get("tmdb_id") or "").strip()
        if detail_tmdb and detail_tmdb != tmdb_id:
            counts["identity_rejected"] += 1
            continue
        proposed = patch.get("proposed_fields")
        if not isinstance(proposed, dict):
            counts["identity_rejected"] += 1
            continue

        updated_fields = 0
        for field, value in proposed.items():
            if field not in ALLOWED_FIELDS or not validate_value(field, value):
                counts["identity_rejected"] += 1
                continue
            current_index = index_record.get(field)
            current_detail = detail_record.get(field)
            if not empty(current_index) or not empty(current_detail):
                if empty(current_index) != empty(current_detail):
                    counts["field_conflict"] += 1
                else:
                    counts["already_filled"] += 1
                continue
            index_record[field] = value
            detail_record[field] = value
            updated_fields += 1
            counts["fields_updated"] += 1
            changed_indexes.add(section)
            changed_shards.add(shard_key)
        if updated_fields:
            counts["records_updated"] += 1

    # Validate all planned changes in memory before publishing any changed files.
    for section in sorted(changed_indexes):
        atomic_write(index_paths[section], indexes[section])
    for shard_key in sorted(changed_shards):
        atomic_write(shard_paths[shard_key], shards[shard_key])

    summary = {
        "report_type": "applied_vod_metadata_patch_summary",
        "catalog_mutated": bool(changed_indexes or changed_shards),
        "read_only": False,
        "counts": counts,
        "updated_index_files": sorted(changed_indexes),
        "updated_detail_shards": len(changed_shards),
        "safety": [
            "Only records with exact catalog ID, existing TMDB ID, and normalized title match were considered.",
            "Only empty metadata fields were filled; existing non-empty fields and all stream sources were preserved.",
            "Only poster_url, year, genres, and overview were eligible; no new TMDB IDs were assigned."
        ]
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/vod-metadata-apply-summary.json"))
    args = parser.parse_args()
    summary = apply_patch(args.root, args.patch, args.output)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
