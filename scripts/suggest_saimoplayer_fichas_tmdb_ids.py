#!/usr/bin/env python3
"""Build exact-title, exact-year TMDB ID candidates from the authorized SaimoPlayer fichas catalog."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series")


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def extract_year(value: Any) -> str:
    match = re.search(r"\(((?:19|20)\d{2})\)\s*$", str(value or ""))
    return match.group(1) if match else ""


def read_fichas(path: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    result: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 3 or fields[0] not in {"f", "s"}:
            continue
        title = fields[1].strip()
        tmdb_id = fields[2].strip()
        if not title or not tmdb_id.isdigit():
            continue
        kind = fields[0]
        result[(kind, norm(title))].append({
            "title": title,
            "tmdb_id": tmdb_id,
            "year": extract_year(title),
        })
    return result


def build_report(root: Path, reference_file: Path) -> dict[str, Any]:
    fichas = read_fichas(reference_file)
    candidates: list[dict[str, Any]] = []
    counts = {
        "catalog_records_without_tmdb_id": 0,
        "exact_title_matches": 0,
        "unique_id_and_exact_year_candidates": 0,
        "ambiguous_reference_ids": 0,
        "missing_catalog_or_reference_year": 0,
        "year_conflicts": 0,
        "no_exact_reference_match": 0,
    }

    for section in SECTIONS:
        index_path = root / f"catalog/vod/index/{section}.json"
        if not index_path.exists():
            continue
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError(f"VOD index must be a list: {index_path}")
        kind = "f" if section == "movies" else "s"
        media_type = "movie" if section == "movies" else "tv"

        for entry in entries:
            if not isinstance(entry, dict) or str(entry.get("tmdb_id") or "").isdigit():
                continue
            title = str(entry.get("title") or "").strip()
            catalog_year = str(entry.get("year") or "").strip()
            if not title:
                continue
            counts["catalog_records_without_tmdb_id"] += 1
            matches = fichas.get((kind, norm(title)), [])
            if not matches:
                counts["no_exact_reference_match"] += 1
                continue
            counts["exact_title_matches"] += 1
            ids = {item["tmdb_id"] for item in matches}
            years = {item["year"] for item in matches if item["year"]}
            if len(ids) != 1:
                counts["ambiguous_reference_ids"] += 1
                continue
            if not catalog_year or not years:
                counts["missing_catalog_or_reference_year"] += 1
                continue
            if years != {catalog_year}:
                counts["year_conflicts"] += 1
                continue

            tmdb_id = next(iter(ids))
            matched_titles = sorted({item["title"] for item in matches})
            counts["unique_id_and_exact_year_candidates"] += 1
            candidates.append({
                "section": section,
                "catalog_id": str(entry.get("id") or ""),
                "catalog_title": title,
                "catalog_year": catalog_year,
                "media_type": media_type,
                "status": "exact_title_review",
                "automatic_update": False,
                "candidates": [{
                    "tmdb_id_candidate": tmdb_id,
                    "matched_title": matched_titles[0],
                    "year": catalog_year,
                    "poster_available": False,
                    "overview_available": False,
                    "reference": "SaimoPlayer/vod/fichas.txt",
                }],
                "reason": "Título normalizado exato, tipo de mídia correspondente, ID único na referência autorizada e ano exato.",
            })

    return {
        "schema_version": 1,
        "report_type": "review_only_tmdb_id_candidates",
        "provider": "Authorized SaimoPlayer fichas reference",
        "read_only": True,
        "catalog_mutated": False,
        "automatic_id_assignment": False,
        "records_examined": counts["catalog_records_without_tmdb_id"],
        "summary": counts,
        "candidates": candidates,
        "safety": [
            "Only exact normalized title and matching media type are considered.",
            "A reference title must provide a year that exactly matches the catalog year.",
            "Ambiguous IDs, missing years, and year conflicts are never assigned.",
            "The existing guarded TMDB ID applier still checks catalog duplicates and already-used IDs.",
            "Only tmdb_id is proposed; no stream, source, or existing metadata is overwritten.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reference-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.root, args.reference_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
