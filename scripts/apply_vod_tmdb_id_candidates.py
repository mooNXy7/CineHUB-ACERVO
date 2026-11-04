#!/usr/bin/env python3
"""Apply only unique exact-title, exact-year TMDB ID candidates; never guess identities."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

# Direct script execution sets sys.path[0] to scripts/, not the repository root.
# Keep checkout-local imports working without requiring network or editable installs.
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from acervo_v2.staging import overlay_path, finalize_overlay
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def apply_reports(root: Path, report_paths: list[Path], output: Path, staging_root: Path) -> dict[str, Any]:
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
        index_paths[section] = overlay_path(root, staging_root, index_path)

    index_lookup: dict[str, dict[str, list[dict]]] = {}
    title_year_counts: dict[str, dict[tuple[str, str], int]] = {}
    tmdb_ids_in_use: dict[str, set[str]] = {"movie": set(), "tv": set()}
    for section, entries in indexes.items():
        by_id: dict[str, list[dict]] = {}
        title_counts: dict[tuple[str, str], int] = {}
        media_group = "movie" if section == "movies" else "tv"
        for item in entries:
            if not isinstance(item, dict):
                continue
            record_id = str(item.get("id") or "")
            if record_id:
                by_id.setdefault(record_id, []).append(item)
            key = (norm(item.get("title")), str(item.get("year") or "").strip())
            title_counts[key] = title_counts.get(key, 0) + 1
            tmdb_id = str(item.get("tmdb_id") or "").strip()
            if tmdb_id:
                tmdb_ids_in_use[media_group].add(tmdb_id)
        index_lookup[section] = by_id
        title_year_counts[section] = title_counts

    shard_id_lookup: dict[str, dict[str, list[dict]]] = {}
    counts = {
        "reports_received": len(report_paths), "candidates_seen": 0,
        "unique_exact_year_candidates": 0, "ids_assigned": 0,
        "skipped_not_exact": 0, "skipped_multiple_candidates": 0,
        "skipped_missing_or_conflicting_year": 0, "skipped_duplicate_title": 0,
        "skipped_tmdb_id_already_used": 0, "skipped_existing_id": 0,
        "skipped_catalog_identity_mismatch": 0,
    }
    changed_indexes: set[str] = set()
    changed_shards: set[str] = set()

    for report_path in report_paths:
        report = load_json(report_path)
        if report.get("report_type") != "review_only_tmdb_id_candidates":
            raise ValueError(f"Unexpected TMDB ID report format: {report_path}")
        if report.get("catalog_mutated") is not False or report.get("read_only") is not True:
            raise ValueError(f"TMDB ID report is not read-only: {report_path}")
        for candidate in report.get("candidates", []):
            counts["candidates_seen"] += 1
            if not isinstance(candidate, dict) or candidate.get("status") != "exact_title_review":
                counts["skipped_not_exact"] += 1
                continue
            options = candidate.get("candidates")
            if not isinstance(options, list) or len(options) != 1:
                counts["skipped_multiple_candidates"] += 1
                continue
            option = options[0]
            tmdb_id = str(option.get("tmdb_id_candidate") or "").strip()
            catalog_year = str(candidate.get("catalog_year") or "").strip()
            candidate_year = str(option.get("year") or "").strip()
            if not (tmdb_id.isdigit() and re.fullmatch(r"(?:19|20)\d{2}", catalog_year)
                    and candidate_year == catalog_year):
                counts["skipped_missing_or_conflicting_year"] += 1
                continue

            section = str(candidate.get("section") or "")
            if section not in indexes:
                counts["skipped_catalog_identity_mismatch"] += 1
                continue
            record_id = str(candidate.get("catalog_id") or "")
            title = str(candidate.get("catalog_title") or "")
            media_type = str(candidate.get("media_type") or "")
            expected_type = "movie" if section == "movies" else "tv"
            if not record_id or not title or media_type != expected_type or norm(title) != norm(option.get("matched_title")):
                counts["skipped_catalog_identity_mismatch"] += 1
                continue
            counts["unique_exact_year_candidates"] += 1

            matching_indexes = index_lookup[section].get(record_id, [])
            if len(matching_indexes) != 1:
                counts["skipped_catalog_identity_mismatch"] += 1
                continue
            index_record = matching_indexes[0]
            if norm(index_record.get("title")) != norm(title) or str(index_record.get("year") or "").strip() != catalog_year:
                counts["skipped_catalog_identity_mismatch"] += 1
                continue
            detail_rel = str(index_record.get("detail_path") or "")
            if not detail_rel:
                counts["skipped_catalog_identity_mismatch"] += 1
                continue
            detail_path = safe_path(root, detail_rel)
            shard_key = detail_path.as_posix()
            if shard_key not in shards:
                shard = load_json(detail_path)
                if not isinstance(shard, list):
                    raise ValueError(f"VOD detail shard is not a list: {detail_rel}")
                shards[shard_key] = shard
                shard_paths[shard_key] = overlay_path(root, staging_root, detail_path)
                by_detail_id: dict[str, list[dict]] = {}
                for item in shard:
                    if isinstance(item, dict) and str(item.get("id") or ""):
                        by_detail_id.setdefault(str(item["id"]), []).append(item)
                shard_id_lookup[shard_key] = by_detail_id
            matching_details = shard_id_lookup[shard_key].get(record_id, [])
            if len(matching_details) != 1:
                counts["skipped_catalog_identity_mismatch"] += 1
                continue
            detail_record = matching_details[0]
            if norm(detail_record.get("title")) != norm(title) or str(detail_record.get("year") or "").strip() != catalog_year:
                counts["skipped_catalog_identity_mismatch"] += 1
                continue

            if str(index_record.get("tmdb_id") or detail_record.get("tmdb_id") or "").strip():
                counts["skipped_existing_id"] += 1
                continue
            title_key = (norm(title), catalog_year)
            if title_year_counts[section].get(title_key, 0) != 1:
                counts["skipped_duplicate_title"] += 1
                continue
            media_group = "movie" if section == "movies" else "tv"
            if tmdb_id in tmdb_ids_in_use[media_group]:
                counts["skipped_tmdb_id_already_used"] += 1
                continue

            index_record["tmdb_id"] = tmdb_id
            detail_record["tmdb_id"] = tmdb_id
            counts["ids_assigned"] += 1
            tmdb_ids_in_use[media_group].add(tmdb_id)
            changed_indexes.add(section)
            changed_shards.add(shard_key)

    for section in sorted(changed_indexes):
        atomic_write(index_paths[section], indexes[section])
    for shard_key in sorted(changed_shards):
        atomic_write(shard_paths[shard_key], shards[shard_key])

    candidate_targets = [index_paths[x] for x in sorted(changed_indexes)] + [shard_paths[x] for x in sorted(changed_shards)]
    candidate_manifest = finalize_overlay(root, staging_root, candidate_targets, {
        "report_type": "applied_exact_title_year_tmdb_id_candidates", "candidates_seen": counts["candidates_seen"],
        "ids_assigned": counts["ids_assigned"],
    })
    summary = {
        "report_type": "applied_exact_title_year_tmdb_id_candidates",
        "catalog_mutated": False,
        "candidate_mutated": bool(candidate_targets),
        "candidate_manifest": str((staging_root / "candidate-manifest.json").as_posix()),
        "read_only": False,
        "counts": counts,
        "updated_index_files": sorted(changed_indexes),
        "updated_detail_shards": len(changed_shards),
        "safety": [
            "Only one TMDB candidate with exact normalized title, exact media type, and exact non-empty year was eligible.",
            "Records with duplicate normalized title/year, an already-used TMDB ID, or any existing provider ID were skipped.",
            "Only tmdb_id was assigned; all existing streams, metadata, IDs, and source records were preserved.",
            "No ambiguous or year-mismatched candidates were assigned.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/tmdb-id-application-summary.json"))
    parser.add_argument("--reports", nargs="+", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    args = parser.parse_args()
    apply_reports(args.root, args.reports, args.output, args.staging_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
