#!/usr/bin/env python3
"""Build a read-only TMDB-ID candidate report through CineHUB's existing Supabase Edge Function.

This script never mutates catalog records or assigns provider IDs automatically.
It reuses the deployed cinehub-catalog function, where TMDB_TOKEN remains server-side.
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
from urllib.request import Request, urlopen
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUPABASE_URL = "https://qdheeiitzlvynshvkwcs.supabase.co"
DEFAULT_FUNCTION_SLUG = "cinehub-catalog"
SECTIONS = ("movies", "series", "anime", "doramas")
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


def search_catalog_proxy(function_url: str, anon_key: str, endpoint: str, title: str,
                         timeout: float = 12.0) -> tuple[list[dict], str]:
    """Call the existing public Supabase proxy; the TMDB credential never leaves Supabase."""
    body = json.dumps({
        "action": "search",
        "type": "movie" if endpoint == "movie" else "series",
        "query": title,
        "page": 1,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if anon_key.strip():
        headers["apikey"] = anon_key.strip()
        headers["Authorization"] = f"Bearer {anon_key.strip()}"
    request = Request(function_url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(2_000_001).decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("success") is False:
            return [], "proxy_error"
        data = payload.get("data", {})
        results = data.get("results", []) if isinstance(data, dict) else []
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


def build_report(root: Path, output: Path, function_url: str, anon_key: str,
                 limit: int = 50, delay: float = 0.25, offset: int = 0) -> dict:
    if not function_url.startswith("https://"):
        raise ValueError("A valid HTTPS CINEHUB_CATALOG_FUNCTION_URL is required.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if offset < 0:
        raise ValueError("offset must be zero or greater")
    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {})
    shard_cache: dict[str, dict[str, dict]] = {}
    examined = 0
    eligible_skipped = 0
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
            if not title:
                continue
            if eligible_skipped < offset:
                eligible_skipped += 1
                continue
            if examined >= limit:
                break
            examined += 1
            counts["no_tmdb_id_examined"] += 1
            endpoint = endpoint_for(section, record)
            year = year_hint(record)
            query_title = re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", title).strip()
            results, status = search_catalog_proxy(function_url, anon_key, endpoint, query_title)
            network_requests += 1
            if status == "auth_error":
                raise RuntimeError("Supabase function authorization failed; verify SUPABASE_ANON_KEY and function access.")
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
            elif year_conflict:
                counts["year_conflict"] += 1
            else:
                counts["no_exact_candidate"] += 1
            if delay > 0:
                time.sleep(delay)
        if examined >= limit:
            break

    report = {
        "schema_version": 1, "report_type": "review_only_tmdb_id_candidates",
        "provider": "CineHUB Supabase Edge Function cinehub-catalog",
        "read_only": True, "catalog_mutated": False, "automatic_id_assignment": False,
        "records_examined": examined, "offset": offset,
        "eligible_records_skipped": eligible_skipped,
        "network_requests": network_requests,
        "summary": counts, "candidates": candidates,
        "notes": [
            "TMDB_TOKEN stays in the Supabase server environment and is never sent to GitHub Actions.",
            "Search results are suggestions only and never change catalog files.",
            "Exact normalized titles can still refer to remakes, regional releases, or different editions.",
            "No stream URLs, API credentials, or authorization headers are included in this report."
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
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--function-url", default=os.environ.get(
        "CINEHUB_CATALOG_FUNCTION_URL",
        f"{DEFAULT_SUPABASE_URL}/functions/v1/{DEFAULT_FUNCTION_SLUG}"))
    parser.add_argument("--anon-key", default=os.environ.get("SUPABASE_ANON_KEY", ""))
    args = parser.parse_args()
    report = build_report(args.root, args.output, args.function_url, args.anon_key,
                          args.limit, max(0.0, args.delay), args.offset)
    print(json.dumps({"records_examined": report["records_examined"],
                      "offset": report["offset"],
                      "eligible_records_skipped": report["eligible_records_skipped"],
                      "network_requests": report["network_requests"],
                      "summary": report["summary"], "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
