#!/usr/bin/env python3
"""Create a review-only TMDB metadata patch; never writes to the catalog."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
API_BASE = "https://api.themoviedb.org/3"
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


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
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def year_hint(value: Any) -> str | None:
    match = re.search(r"\(((?:19|20)\d{2})\)\s*$", str(value or ""))
    return match.group(1) if match else None


def endpoint_for(section: str, record: dict) -> str:
    return "movie" if section == "movies" or record.get("type") == "movie" else "tv"


def fetch_tmdb_details(endpoint: str, tmdb_id: str, api_key: str, timeout: float = 8.0,
                       retries: int = 3, delay: float = 0.25) -> tuple[dict | None, str]:
    """Fetch one exact TMDB ID. Errors are redacted; the API key is never logged."""
    url = f"{API_BASE}/{endpoint}/{tmdb_id}?{urlencode({'api_key': api_key, 'language': 'pt-BR'})}"
    last_status = "request_error"
    for attempt in range(retries):
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "CineHUB-ACERVO-MetadataAudit/1.0"})
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read(2_000_001).decode("utf-8"))
            if not isinstance(payload, dict) or str(payload.get("id") or "") != tmdb_id:
                return None, "provider_id_mismatch"
            return payload, "ok"
        except HTTPError as exc:
            if exc.code == 404:
                return None, "not_found"
            last_status = f"http_{exc.code}"
            if exc.code not in {429, 500, 502, 503, 504}:
                return None, last_status
            retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
            try:
                wait = min(10.0, max(delay, float(retry_after)))
            except (TypeError, ValueError):
                wait = delay * (attempt + 1)
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            last_status = "request_error"
            wait = delay * (attempt + 1)
        if attempt + 1 < retries:
            time.sleep(wait)
    return None, last_status


def response_metadata(payload: dict, endpoint: str) -> dict:
    date_field = "release_date" if endpoint == "movie" else "first_air_date"
    title_fields = ("title", "original_title") if endpoint == "movie" else ("name", "original_name")
    return {
        "id": str(payload.get("id") or ""),
        "titles": [str(payload.get(key) or "") for key in title_fields if payload.get(key)],
        "year": str(payload.get(date_field) or "")[:4] or None,
        "poster_url": IMAGE_BASE + str(payload["poster_path"]) if payload.get("poster_path") else None,
        "genres": [str(g.get("name")).strip() for g in payload.get("genres", [])
                   if isinstance(g, dict) and str(g.get("name") or "").strip()],
    }


def init_cache(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS tmdb_details (
            endpoint TEXT NOT NULL,
            tmdb_id TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT,
            checked_at TEXT NOT NULL,
            PRIMARY KEY(endpoint, tmdb_id)
        )
    """)
    db.commit()
    return db


def cached_details(db: sqlite3.Connection, endpoint: str, tmdb_id: str) -> tuple[dict | None, str] | None:
    row = db.execute(
        "SELECT status, payload_json FROM tmdb_details WHERE endpoint=? AND tmdb_id=?",
        (endpoint, tmdb_id),
    ).fetchone()
    if not row:
        return None
    status, raw = row
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return None
    return (payload if isinstance(payload, dict) else None, status)


def store_details(db: sqlite3.Connection, endpoint: str, tmdb_id: str,
                  payload: dict | None, status: str) -> None:
    db.execute(
        """INSERT INTO tmdb_details(endpoint, tmdb_id, status, payload_json, checked_at)
           VALUES(?,?,?,?,?)
           ON CONFLICT(endpoint, tmdb_id) DO UPDATE SET
             status=excluded.status, payload_json=excluded.payload_json, checked_at=excluded.checked_at""",
        (endpoint, tmdb_id, status, json.dumps(payload, ensure_ascii=False) if payload else None,
         datetime.now(timezone.utc).isoformat()),
    )
    db.commit()


def build_patch(root: Path, output: Path, cache_path: Path, limit: int,
                api_key: str, delay: float = 0.25) -> dict:
    if not api_key.strip():
        raise ValueError("TMDB_API_KEY is required; provide it through a secret or environment variable.")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")

    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {})
    db = init_cache(cache_path)
    detail_cache: dict[str, dict[str, dict]] = {}
    network_requests = 0
    examined = 0
    patches = []
    counts = {"ready": 0, "identity_review": 0, "not_found": 0, "request_error": 0, "complete": 0, "no_tmdb_id": 0}

    try:
        for section in SECTIONS:
            # A minimal fixture or future schema may omit an entire category; only
            # skip it when the manifest does not declare it. Declared missing files still fail loudly.
            if section not in categories:
                continue
            info = categories[section]
            index_path = info.get("index_path", f"catalog/vod/index/{section}.json")
            index_records = load_json(safe_path(root, index_path))
            if not isinstance(index_records, list):
                raise ValueError(f"VOD index for {section} is not a list")
            for entry in index_records:
                if not isinstance(entry, dict):
                    continue
                detail_path = str(entry.get("detail_path") or "")
                if not detail_path:
                    continue
                resolved = safe_path(root, detail_path)
                key_path = resolved.as_posix()
                if key_path not in detail_cache:
                    shard = load_json(resolved)
                    if not isinstance(shard, list):
                        raise ValueError(f"VOD detail shard is not a list: {detail_path}")
                    detail_cache[key_path] = {
                        str(item.get("id")): item for item in shard
                        if isinstance(item, dict) and item.get("id")
                    }
                record = detail_cache[key_path].get(str(entry.get("id") or ""))
                if not isinstance(record, dict):
                    continue
                missing = [field for field in ("poster_url", "year", "genres")
                           if record.get(field) is None or record.get(field) == "" or record.get(field) == []]
                if not missing:
                    counts["complete"] += 1
                    continue
                tmdb_id = str(record.get("tmdb_id") or entry.get("tmdb_id") or "").strip()
                if not tmdb_id.isdigit():
                    counts["no_tmdb_id"] += 1
                    continue
                if examined >= limit:
                    break
                examined += 1
                endpoint = endpoint_for(section, record)
                cached = cached_details(db, endpoint, tmdb_id)
                if cached is None:
                    payload, status = fetch_tmdb_details(endpoint, tmdb_id, api_key, delay=delay)
                    network_requests += 1
                    if status in {"ok", "not_found", "provider_id_mismatch"}:
                        store_details(db, endpoint, tmdb_id, payload, status)
                else:
                    payload, status = cached

                if status in {"http_401", "http_403"}:
                    raise RuntimeError("TMDB authentication failed; verify the TMDB_API_KEY secret.")
                if status != "ok" or not isinstance(payload, dict):
                    counts["not_found" if status == "not_found" else "request_error"] += 1
                    continue
                meta = response_metadata(payload, endpoint)
                if meta["id"] != tmdb_id:
                    counts["identity_review"] += 1
                    continue
                record_title = norm(record.get("title"))
                provider_titles = {norm(t) for t in meta["titles"] if norm(t)}
                if not record_title or record_title not in provider_titles:
                    counts["identity_review"] += 1
                    continue
                hint = year_hint(record.get("title"))
                if hint and meta.get("year") and hint != meta["year"]:
                    counts["identity_review"] += 1
                    continue

                proposed = {}
                if "poster_url" in missing and meta.get("poster_url"):
                    proposed["poster_url"] = meta["poster_url"]
                if "year" in missing and meta.get("year"):
                    proposed["year"] = meta["year"]
                if "genres" in missing and meta.get("genres"):
                    proposed["genres"] = meta["genres"]
                if not proposed:
                    counts["complete"] += 1
                    continue
                counts["ready"] += 1
                patches.append({
                    "section": section,
                    "id": str(record.get("id") or ""),
                    "title": str(record.get("title") or ""),
                    "tmdb_id": tmdb_id,
                    "matched_title": meta["titles"][0] if meta["titles"] else "",
                    "missing_fields": missing,
                    "proposed_fields": proposed,
                    "confidence": "exact_provider_id_and_title",
                    "source": "TMDB",
                })
                if delay > 0:
                    time.sleep(delay)
            if examined >= limit:
                break
    finally:
        db.close()

    report = {
        "schema_version": 1,
        "report_type": "review_only_tmdb_metadata_patch",
        "read_only": True,
        "catalog_mutated": False,
        "network_requests": network_requests,
        "records_examined": examined,
        "summary": counts,
        "patches": patches,
        "notes": [
            "This report proposes changes only; it never writes to catalog JSON files.",
            "Only existing numeric TMDB IDs are queried; no title search or new ID assignment is performed.",
            "Proposals require exact provider ID and a normalized title match. A year in the catalog title that conflicts with TMDB is held for review.",
            "Only currently missing poster_url, year, and genres fields are proposed; existing non-empty metadata is never overwritten.",
            "API credentials and full provider responses are excluded from this report.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/vod-metadata-patch.json"))
    parser.add_argument("--cache", type=Path, default=Path("/tmp/cinehub-tmdb-cache.sqlite3"))
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()
    key = os.environ.get("TMDB_API_KEY", "")
    report = build_patch(args.root, args.output, args.cache, args.limit, key, max(0.0, args.delay))
    print(json.dumps({
        "output": str(args.output),
        "records_examined": report["records_examined"],
        "network_requests": report["network_requests"],
        "summary": report["summary"],
        "catalog_mutated": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
