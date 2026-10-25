#!/usr/bin/env python3
"""Fetch conservative TMDB metadata candidates without mutating the ACERVO catalog."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
TARGET_FIELDS = ("poster_url", "year", "genres")
TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
MAX_LIMIT = 500


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"\b(?:4k|uhd|fhd|hd|1080p|720p|sd)\b", " ", value, flags=re.I)
    value = re.sub(r"\s*\((?:19|20)\d{2}\)\s*$", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def safe_catalog_path(root: Path, relative: str) -> Path:
    base = root.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"VOD index path escapes repository root: {relative}")
    return candidate


def missing_fields(record: dict[str, Any]) -> list[str]:
    return [
        field for field in TARGET_FIELDS
        if record.get(field) is None or record.get(field) == "" or record.get(field) == []
    ]


def year_from_date(value: Any) -> str | None:
    match = re.match(r"^(19|20)\d{2}", str(value or ""))
    return match.group(0) if match else None


def provider_title(payload: dict[str, Any]) -> tuple[str, str]:
    return (
        str(payload.get("title") or payload.get("name") or "").strip(),
        str(payload.get("original_title") or payload.get("original_name") or "").strip(),
    )


def match_confidence(record: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str, str | None]:
    expected = norm(record.get("title"))
    localized, original = provider_title(payload)
    if not expected or expected not in {norm(localized), norm(original)}:
        return False, "title_mismatch", None
    provider_year = year_from_date(payload.get("release_date") or payload.get("first_air_date"))
    existing_year = str(record.get("year") or "").strip()
    if existing_year and provider_year and existing_year != provider_year:
        return False, "year_mismatch", provider_year
    return True, "exact_title_match", provider_year


def connect_cache(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS tmdb_cache ("
        "media_type TEXT NOT NULL, tmdb_id TEXT NOT NULL, fetched_at INTEGER NOT NULL, "
        "payload TEXT NOT NULL, PRIMARY KEY(media_type, tmdb_id))"
    )
    connection.commit()
    return connection


def cached_payload(cache: sqlite3.Connection, media_type: str, tmdb_id: str) -> dict[str, Any] | None:
    row = cache.execute(
        "SELECT fetched_at, payload FROM tmdb_cache WHERE media_type=? AND tmdb_id=?",
        (media_type, tmdb_id),
    ).fetchone()
    if not row or int(time.time()) - int(row[0]) > CACHE_TTL_SECONDS:
        return None
    try:
        payload = json.loads(row[1])
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def fetch_payload(
    media_type: str,
    tmdb_id: str,
    api_key: str,
    cache: sqlite3.Connection,
    timeout: float = 8.0,
    retries: int = 3,
) -> tuple[dict[str, Any] | None, str]:
    cached = cached_payload(cache, media_type, tmdb_id)
    if cached is not None:
        return cached, "cache"
    kind = "movie" if media_type == "movie" else "tv"
    query = urllib.parse.urlencode({"api_key": api_key, "language": "pt-BR"})
    url = f"{TMDB_BASE}/{kind}/{urllib.parse.quote(tmdb_id)}?{query}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "CineHUB-ACERVO-MetadataAudit/1.0"},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise OSError(f"TMDB HTTP status {response.status}")
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                return None, "response_too_large"
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("success") is False:
                return None, "invalid_provider_response"
            cache.execute(
                "INSERT OR REPLACE INTO tmdb_cache(media_type, tmdb_id, fetched_at, payload) "
                "VALUES (?, ?, ?, ?)",
                (media_type, tmdb_id, int(time.time()), json.dumps(payload, ensure_ascii=False)),
            )
            cache.commit()
            return payload, "fetched"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None, "not_found"
            if exc.code not in {429, 500, 502, 503, 504} or attempt + 1 >= retries:
                return None, f"http_{exc.code}"
        except (OSError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError):
            if attempt + 1 >= retries:
                return None, "fetch_error"
        time.sleep(min(2 ** attempt, 4))
    return None, "fetch_error"


def build_candidates(
    root: Path,
    output: Path,
    *,
    fetch: bool = False,
    limit: int = 100,
    cache_path: Path | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {}) if isinstance(manifest, dict) else {}
    eligible: list[tuple[str, dict[str, Any], list[str]]] = []
    for section in SECTIONS:
        info = categories.get(section, {}) if isinstance(categories, dict) else {}
        index_path = info.get("index_path", f"catalog/vod/index/{section}.json")
        records = load_json(safe_catalog_path(root, index_path))
        if not isinstance(records, list):
            raise ValueError(f"VOD index for {section} must be a JSON list")
        for record in records:
            if not isinstance(record, dict):
                continue
            missing = missing_fields(record)
            tmdb_id = str(record.get("tmdb_id") or "").strip()
            if missing and tmdb_id.isdigit():
                eligible.append((section, record, missing))
                if len(eligible) >= limit:
                    break
        if len(eligible) >= limit:
            break

    if fetch and not api_key:
        raise ValueError("TMDB_API_KEY is required when --fetch is used; no catalog changes were made.")

    cache = connect_cache(cache_path or (Path.home() / ".cache" / "cinehub-acervo" / "tmdb.sqlite3")) if fetch else None
    candidates = []
    review = []
    failures = []
    try:
        for section, record, missing in eligible:
            entry = {
                "category": section,
                "id": str(record.get("id") or ""),
                "title": str(record.get("title") or ""),
                "tmdb_id": str(record.get("tmdb_id") or ""),
                "missing_fields": missing,
            }
            if not fetch:
                candidates.append({**entry, "status": "eligible_id_present_not_fetched"})
                continue
            media_type = "movie" if section == "movies" else "tv"
            payload, source = fetch_payload(media_type, entry["tmdb_id"], api_key or "", cache)
            if payload is None:
                failures.append({**entry, "status": source})
                continue
            matched, match_status, provider_year = match_confidence(record, payload)
            if not matched:
                review.append({**entry, "status": match_status, "provider_title": provider_title(payload)[0]})
                continue
            patch: dict[str, Any] = {}
            poster_path = payload.get("poster_path")
            if "poster_url" in missing and isinstance(poster_path, str) and poster_path.startswith("/") and ".." not in poster_path:
                patch["poster_url"] = IMAGE_BASE + poster_path
            if "year" in missing and provider_year:
                patch["year"] = provider_year
            if "genres" in missing and isinstance(payload.get("genres"), list):
                genres = [
                    str(item.get("name")).strip()
                    for item in payload["genres"]
                    if isinstance(item, dict) and str(item.get("name") or "").strip()
                ]
                if genres:
                    patch["genres"] = list(dict.fromkeys(genres))
            if patch:
                candidates.append({
                    **entry,
                    "status": "candidate_exact_title_match",
                    "provider_title": provider_title(payload)[0],
                    "provider_year": provider_year,
                    "cache_status": source,
                    "patch": patch,
                    "requires_review_before_apply": True,
                })
            else:
                candidates.append({**entry, "status": "no_safe_fields_to_fill", "cache_status": source})
    finally:
        if cache is not None:
            cache.close()

    return {
        "schema_version": 1,
        "report_type": "tmdb_metadata_candidate_patch",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "network_accessed": bool(fetch),
        "catalog_mutated": False,
        "provider": "TMDB",
        "candidate_limit": limit,
        "eligible_records_found": len(eligible),
        "patch_candidates": candidates,
        "manual_review": review,
        "fetch_failures": failures,
        "notes": [
            "Este relatório nunca escreve no catálogo; ele gera candidatos para revisão.",
            "Somente registros com tmdb_id numérico são consultados; títulos sem ID não são pesquisados automaticamente.",
            "Correspondência exige título localizado/original exato após normalização e ano compatível.",
            "IDs, pôsteres, anos e gêneros existentes nunca são substituídos por esta ferramenta.",
            "A chave TMDB vem exclusivamente de TMDB_API_KEY e não é gravada no cache nem no relatório.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "tmdb-metadata-candidates.json")
    parser.add_argument("--limit", type=int, default=100, help=f"máximo de registros por execução (1-{MAX_LIMIT})")
    parser.add_argument("--fetch", action="store_true", help="consultar TMDB; exige TMDB_API_KEY; catálogo permanece somente leitura")
    parser.add_argument("--cache", type=Path, help="caminho do cache SQLite; padrão no cache do usuário")
    args = parser.parse_args()
    api_key = os.environ.get("TMDB_API_KEY")
    report = build_candidates(
        args.root, args.output, fetch=args.fetch, limit=args.limit,
        cache_path=args.cache, api_key=api_key,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "eligible_records_found": report["eligible_records_found"],
        "patch_candidates": len(report["patch_candidates"]),
        "manual_review": len(report["manual_review"]),
        "fetch_failures": len(report["fetch_failures"]),
        "network_accessed": report["network_accessed"],
        "catalog_mutated": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
