#!/usr/bin/env python3
"""Build a review-only TMDB title-search report for VOD records missing provider IDs.

This script never mutates catalog files and never assigns TMDB IDs. It only emits
candidates when title normalization is exact and, when both are known, years agree.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
API_BASE = "https://api.themoviedb.org/3"
MAX_LIMIT = 500


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_path(root: Path, relative: str) -> Path:
    base = root.resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ValueError(f"Catalog path escapes repository root: {relative}")
    return path


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def year_hint(record: dict) -> str | None:
    year = str(record.get("year") or "").strip()
    if re.fullmatch(r"(?:19|20)\d{2}", year):
        return year
    match = re.search(r"\(((?:19|20)\d{2})\)\s*$", str(record.get("title") or ""))
    return match.group(1) if match else None


def endpoint_for(section: str, record: dict) -> str:
    return "movie" if section == "movies" or record.get("type") == "movie" else "tv"


def search_tmdb(endpoint: str, title: str, year: str | None, api_key: str,
                timeout: float = 8.0) -> tuple[list[dict], str]:
    params = {"api_key": api_key, "query": title, "language": "pt-BR", "include_adult": "false"}
    if year and endpoint == "movie":
        params["year"] = year
    if year and endpoint == "tv":
        params["first_air_date_year"] = year
    url = f"{API_BASE}/search/{endpoint}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "CineHUB-ACERVO-VODReview/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(1_000_001).decode("utf-8"))
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return ([x for x in results if isinstance(x, dict)], "ok")
    except HTTPError as exc:
        if exc.code in {401, 403}:
            return [], "auth_error"
        return [], f"http_{exc.code}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [], "request_error"


def result_title(item: dict, endpoint: str) -> str:
    keys = ("title", "original_title") if endpoint == "movie" else ("name", "original_name")
    for key in keys:
        if item.get(key):
            return str(item[key])
    return ""


def result_year(item: dict, endpoint: str) -> str | None:
    field = "release_date" if endpoint == "movie" else "first_air_date"
    value = str(item.get(field) or "")
    return value[:4] if re.match(r"^(?:19|20)\d{2}", value) else None


def build_report(root: Path, output: Path, api_key: str, limit: int = 50,
                 delay: float = 0.25) -> dict:
    if not api_key.strip():
        raise ValueError("TMDB_API_KEY is required.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {})
    shard_cache: dict[str, dict[str, dict]] = {}
    examined = 0
    network_requests = 0
    candidates: list[dict] = []
    counts = {"no_tmdb_id_examined": 0, "exact_title_candidates": 0,
              "year_conflict": 0, "no_exact_candidate": 0, "request_error": 0}

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
            detail_path = str(entry.get("detail_path") or "")
            if not detail_path:
                continue
            resolved = safe_path(root, detail_path)
            key = resolved.as_posix()
            if key not in shard_cache:
                shard = load_json(resolved)
                if not isinstance(shard, list):
                    raise ValueError(f"VOD detail shard is not a list: {detail_path}")
                shard_cache[key] = {str(x.get("id")): x for x in shard
                                    if isinstance(x, dict) and x.get("id")}
            record = shard_cache[key].get(str(entry.get("id") or ""))
            if not isinstance(record, dict):
                continue
            tmdb_id = str(record.get("tmdb_id") or entry.get("tmdb_id") or "").strip()
            if tmdb_id.isdigit():
                continue
            title = str(record.get("title") or "").strip()
            if not title or examined >= limit:
                if examined >= limit:
                    break
                continue
            examined += 1
            counts["no_tmdb_id_examined"] += 1
            endpoint = endpoint_for(section, record)
            year = year_hint(record)
            results, status = search_tmdb(endpoint, re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", title), year, api_key)
            network_requests += 1
            if status == "auth_error":
                raise RuntimeError("TMDB authentication failed; verify the TMDB_API_KEY secret.")
            if status != "ok":
                counts["request_error"] += 1
                continue
            matches = []
            year_conflict = False
            for item in results:
                candidate_title = result_title(item, endpoint)
                if not candidate_title or norm(candidate_title) != norm(title):
                    continue
                candidate_year = result_year(item, endpoint)
                if year and candidate_year and year != candidate_year:
                    year_conflict = True
                    continue
                if not str(item.get("id") or "").isdigit():
                    continue
                matches.append({
                    "tmdb_id_candidate": str(item["id"]),
                    "matched_title": candidate_title,
                    "original_title": str(item.get("original_title") or item.get("original_name") or ""),
                    "year": candidate_year,
                    "poster_available": bool(item.get("poster_path")),
                    "overview_available": bool(item.get("overview")),
                })
            if matches:
                counts["exact_title_candidates"] += 1
                candidates.append({
                    "section": section, "catalog_id": str(record.get("id") or ""),
                    "catalog_title": title, "catalog_year": year,
                    "media_type": endpoint, "status": "exact_title_review",
                    "automatic_update": False, "candidates": matches[:5],
                    "reason": "Título normalizado exato; confirmar identidade, edição e ano antes de associar o ID."
                })
            else:
                if year_conflict:
                    counts["year_conflict"] += 1
                else:
                    counts["no_exact_candidate"] += 1
            if delay > 0:
                time.sleep(delay)
        if examined >= limit:
            break

    report = {
        "schema_version": 1, "report_type": "review_only_tmdb_id_candidates",
        "read_only": True, "catalog_mutated": False, "automatic_id_assignment": False,
        "records_examined": examined, "network_requests": network_requests,
        "summary": counts, "candidates": candidates,
        "notes": [
            "Search results are suggestions only and never change catalog files.",
            "Exact normalized titles can still refer to remakes, regional releases, or different editions.",
            "No stream URLs or API credentials are included in this report."
        ]
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()
    report = build_report(args.root, args.output, os.environ.get("TMDB_API_KEY", ""),
                          args.limit, max(0.0, args.delay))
    print(json.dumps({"records_examined": report["records_examined"],
                      "network_requests": report["network_requests"],
                      "summary": report["summary"], "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
