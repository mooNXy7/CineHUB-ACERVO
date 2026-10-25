#!/usr/bin/env python3
"""Importa catálogo de canais e VOD do diretório de referência para o CineHUB ACERVO.

O processo é incremental e idempotente: preserva registros existentes, junta fontes
sem duplicar URLs e nunca publica URLs com credenciais evidentes ou hosts privados.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = Path("/tmp/cinehub-reference")
CHANNELS_FILE = ROOT / "catalog/channels/channels.json"
RADIOS_FILE = ROOT / "catalog/radios/radios.json"
VOD_INDEX = ROOT / "catalog/vod/index.json"
DETAILS = ROOT / "catalog/vod/details"
REPORT = ROOT / "reports/reference-import.json"
SOURCE_ID = "reference-catalog"
SENSITIVE_QUERY = {
    "token", "access_token", "auth", "authorization", "password", "passwd",
    "username", "user", "key", "signature", "sig", "session", "expires", "hash",
}
CREDENTIAL_PATH = re.compile(
    r"/(?:live|movie|series|timeshift)/[^/]{3,}/[^/]{3,}/", re.I
)
URL_RE = re.compile(r"https?://[^\s,<>\"']+", re.I)


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def base_title(value: str) -> str:
    value = re.sub(r"\s*\((?:19|20)\d{2}\)\s*$", "", str(value or ""))
    value = re.sub(r"\b(?:4k|uhd|fhd|hd|1080p|720p|sd)\b", "", value, flags=re.I)
    return norm(value)


def canonical_key(item: dict) -> tuple:
    tmdb_id = str(item.get("tmdb_id") or "").strip()
    if tmdb_id:
        return ("tmdb", tmdb_id)
    title = base_title(item.get("title", ""))
    year = str(item.get("year") or "")
    if not year:
        match = re.search(r"\(((?:19|20)\d{2})\)\s*$", str(item.get("title") or ""))
        year = match.group(1) if match else ""
    if title:
        return ("title", title, year)
    return ("id", str(item.get("id") or ""))


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(value)).strip("-") or "item"


def letter(value: str) -> str:
    first = norm(value)[:1].upper()
    return first if "A" <= first <= "Z" else "#"


def safe_candidate(raw: str) -> bool:
    try:
        parsed = urlsplit(str(raw).strip().rstrip(".,;"))
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if any(k.lower() in SENSITIVE_QUERY for k, _ in parse_qsl(parsed.query)):
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                    or ip.is_multicast or ip.is_unspecified):
                return False
        except ValueError:
            pass
        if CREDENTIAL_PATH.search(parsed.path):
            return False
        return True
    except (TypeError, ValueError):
        return False


def load_json(path: Path, fallback: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def atomic_write_text(path: Path, text: str) -> None:
    """Replace one generated file atomically; preserve prior content on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, value: dict | list) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\\n")


def write_json_compact(path: Path, value: dict | list) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\\n")


def read_lines(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        yield from stream


def split_sources(text: str, audio: str = "dub", source_id: str = SOURCE_ID,
                  priority: int = 50) -> tuple[list[dict], list[dict], int]:
    urls, refs, skipped = [], [], 0
    for token in (text or "").split(","):
        token = token.strip()
        if not token:
            continue
        if token.lower().startswith(("http://", "https://")):
            clean = token.rstrip(".,;")
            if safe_candidate(clean):
                host = (urlsplit(clean).hostname or "").lower()
                source_type = "embed" if host in {"mgeb.top"} else "direct"
                urls.append({
                    "url": clean, "audio": audio, "priority": priority,
                    "source_id": source_id, "source_type": source_type
                })
            else:
                skipped += 1
        elif re.match(r"^\d+:[A-Za-z0-9._/?=&%+-]+$", token):
            provider, ident = token.split(":", 1)
            refs.append({"provider": provider, "ref": ident, "audio": audio, "source_id": source_id})
    return urls, refs, skipped


def merge_sources(target: list[dict], incoming: list[dict]) -> int:
    by_url = {s.get("url"): s for s in target if isinstance(s, dict) and s.get("url")}
    added = 0
    for source in incoming:
        url = source.get("url")
        if not url:
            continue
        if url not in by_url:
            target.append(source)
            by_url[url] = source
            added += 1
        else:
            existing = by_url[url]
            for field, value in source.items():
                if field not in existing and value is not None:
                    existing[field] = value
    return added


def merge_provider_refs(target: list[dict], incoming: list[dict]) -> int:
    known = {(x.get("provider"), x.get("ref"), x.get("audio")) for x in target}
    added = 0
    for item in incoming:
        key = (item.get("provider"), item.get("ref"), item.get("audio"))
        if key not in known:
            target.append(item)
            known.add(key)
            added += 1
    return added


def read_fichas(path: Path) -> dict[tuple[str, str], dict]:
    result = {}
    for line in read_lines(path) or ():
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 2 or fields[0] not in {"f", "s"}:
            continue
        kind, title = fields[0], fields[1].strip()
        if not title:
            continue
        result[(kind, norm(title))] = {
            "tmdb_id": fields[2] if len(fields) > 2 and fields[2].isdigit() else None,
            "poster_path": fields[3] if len(fields) > 3 and fields[3] else None,
            "genres": [g.strip() for g in fields[4].split(",") if g.strip()] if len(fields) > 4 else [],
        }
    return result


def parse_featured(path: Path) -> tuple[dict, set, set]:
    posters, anime, doramas = {}, set(), set()
    section = ""
    for line in read_lines(path) or ():
        fields = line.rstrip("\n").split("\t")
        if len(fields) >= 2 and fields[0] == "fila":
            section = fields[1].strip().casefold()
            continue
        if len(fields) >= 5 and fields[0] in {"f", "s", "a", "d"}:
            row_kind, title = fields[0], fields[1].strip()
            kind = "f" if row_kind == "f" else "s"
            poster = fields[4].strip()
            if poster:
                posters[(kind, norm(title))] = poster if poster.startswith("http") else "https://image.tmdb.org/t/p/w342" + poster
            if kind == "s" and (row_kind == "a" or "anime" in section or "anima" in section):
                anime.add(norm(title))
            if kind == "s" and (row_kind == "d" or "dorama" in section or "drama asi" in section):
                doramas.add(norm(title))
    return posters, anime, doramas


def parse_search_index(path: Path) -> tuple[dict, dict]:
    movies, series = {}, {}
    for line in read_lines(path) or ():
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 3 or fields[1] not in {"f", "s"}:
            continue
        title, kind = fields[0].strip(), fields[1]
        year = fields[3].strip() if len(fields) > 3 and fields[3].strip().isdigit() else None
        if not title:
            continue
        if kind == "f":
            match = re.search(r"\(((?:19|20)\d{2})\)\s*$", title)
            year = year or (match.group(1) if match else None)
            movies[norm(title)] = {
                "id": "movie-" + slug(title), "title": title, "type": "movie",
                "year": year, "poster_url": None, "genres": [], "tmdb_id": None,
                "sources": [], "provider_refs": [], "source_candidates_skipped": 0,
            }
        else:
            key = (norm(title), year or "")
            series[key] = {
                "id": "series-" + slug(title) + ("-" + year if year else ""),
                "title": title, "type": "series", "year": year,
                "poster_url": None, "genres": [], "tmdb_id": None,
                "seasons": {}, "sources": [], "provider_refs": [],
                "source_candidates_skipped": 0,
            }
    return movies, series


def parse_movies(reference: Path, fichas: dict, featured_posters: dict, counters: dict, movies=None) -> dict:
    movies = movies or {}
    vod = reference / "vod"
    for path in sorted(vod.glob("filmes-*.txt")):
        for line in read_lines(path) or ():
            line = line.rstrip("\n")
            if not line or line.startswith("#") or "\t" not in line:
                continue
            fields = line.split("\t")
            title = fields[0].strip()
            if not title:
                continue
            key = norm(title)
            item = movies.setdefault(key, {
                "id": "movie-" + slug(title), "title": title, "type": "movie",
                "year": (re.search(r"\(((?:19|20)\d{2})\)\s*$", title) or [None, None])[1],
                "poster_url": None, "genres": [], "tmdb_id": None,
                "sources": [], "provider_refs": [], "source_candidates_skipped": 0,
            })
            for field in fields[1:]:
                if "=" not in field:
                    continue
                audio, value = field.split("=", 1)
                if audio not in {"dub", "leg"}:
                    continue
                urls, refs, skipped = split_sources(value, audio)
                counters["skipped_urls"] += skipped
                item["source_candidates_skipped"] += skipped
                counters["sources_added"] += merge_sources(item["sources"], urls)
                counters["provider_refs_added"] += merge_provider_refs(item["provider_refs"], refs)
    for item in movies.values():
        meta = fichas.get(("f", norm(item["title"])), {})
        item["tmdb_id"] = meta.get("tmdb_id")
        item["poster_url"] = meta.get("poster_path") or featured_posters.get(("f", norm(item["title"])))
        item["genres"] = meta.get("genres", [])
    return movies



def parse_extra_movie_sources(reference: Path, movies: dict, fichas: dict, counters: dict) -> dict:
    vod = reference / "vod"
    source_files = (
        (vod / "redeflix" / "links-filmes.txt", "reference-redeflix"),
        (vod / "mgeb" / "links-filmes.txt", "reference-mgeb"),
    )
    by_tmdb = {str(item.get("tmdb_id")): item for item in movies.values() if item.get("tmdb_id")}
    by_title = {}
    for item in movies.values():
        for key in {norm(item.get("title", "")), base_title(item.get("title", ""))}:
            if key:
                by_title.setdefault(key, item)
    for path, source_id in source_files:
        for raw in read_lines(path) or ():
            line = raw.rstrip("\n")
            if not line or line.startswith("#") or "\t" not in line:
                continue
            fields = line.split("\t")
            title = fields[0].strip()
            if not title:
                continue
            tmdb_id = next((field.split("=", 1)[1].strip() for field in fields[1:]
                            if field.startswith("tmdb=") and field.split("=", 1)[1].strip().isdigit()), None)
            if not tmdb_id:
                for field in fields[1:]:
                    match = re.search(r"https?://mgeb\.top/embed/(\d+)", field)
                    if match:
                        tmdb_id = match.group(1)
                        break
            item = by_tmdb.get(tmdb_id) if tmdb_id else None
            item = item or movies.get(norm(title)) or by_title.get(norm(title)) or by_title.get(base_title(title))
            if item is None:
                year_match = re.search(r"\(((?:19|20)\d{2})\)\s*$", title)
                item = {
                    "id": "movie-" + slug(title), "title": title, "type": "movie",
                    "year": year_match.group(1) if year_match else None,
                    "poster_url": None, "genres": [], "tmdb_id": tmdb_id,
                    "sources": [], "provider_refs": [], "source_candidates_skipped": 0,
                }
                movies[norm(title)] = item
            if tmdb_id:
                item["tmdb_id"] = item.get("tmdb_id") or tmdb_id
                by_tmdb[tmdb_id] = item
            for key in {norm(item.get("title", "")), base_title(item.get("title", ""))}:
                if key:
                    by_title[key] = item
            meta = fichas.get(("f", norm(item["title"])), {})
            item["poster_url"] = item.get("poster_url") or meta.get("poster_path")
            item["genres"] = item.get("genres") or meta.get("genres", [])
            for field in fields[1:]:
                if "=" not in field:
                    continue
                audio, value = field.split("=", 1)
                if audio not in {"dub", "leg"}:
                    continue
                urls, refs, skipped = split_sources(value, audio, source_id=source_id, priority=20)
                counters["skipped_urls"] += skipped
                item["source_candidates_skipped"] = int(item.get("source_candidates_skipped", 0)) + skipped
                counters["sources_added"] += merge_sources(item.setdefault("sources", []), urls)
                counters["provider_refs_added"] += merge_provider_refs(item.setdefault("provider_refs", []), refs)
    return movies


def parse_series(reference: Path, fichas: dict, featured_posters: dict, featured_anime: set,
                 featured_doramas: set, counters: dict, series=None) -> dict:
    series = series or {}
    vod = reference / "vod"
    for path in sorted(vod.glob("series-*-*.txt")):
        current = None
        for raw in read_lines(path) or ():
            line = raw.rstrip("\n")
            if not line:
                continue
            if line.startswith("@"):
                fields = line[1:].split("\t")
                title = fields[0].strip()
                year = fields[1].strip() if len(fields) > 1 and fields[1].strip().isdigit() else None
                if not title:
                    current = None
                    continue
                key = (norm(title), year or "")
                current = series.setdefault(key, {
                    "id": "series-" + slug(title) + ("-" + year if year else ""),
                    "title": title, "type": "series", "year": year,
                    "poster_url": None, "genres": [], "tmdb_id": None,
                    "seasons": {}, "sources": [], "provider_refs": [],
                    "source_candidates_skipped": 0,
                })
                continue
            if current is None:
                continue
            fields = line.split("\t")
            if len(fields) < 4 or not fields[0].isdigit() or not fields[1].isdigit():
                continue
            season_no, episode_no, audio = int(fields[0]), int(fields[1]), fields[2].strip().lower()
            urls, refs, skipped = split_sources(fields[3], audio)
            counters["skipped_urls"] += skipped
            current["source_candidates_skipped"] += skipped
            season = current["seasons"].setdefault(str(season_no), {"season": season_no, "episodes": []})
            episode_key = (episode_no, audio)
            existing = next((e for e in season["episodes"] if (e["episode"], e["audio"]) == episode_key), None)
            if existing is None:
                existing = {"episode": episode_no, "audio": audio, "sources": [], "provider_refs": []}
                season["episodes"].append(existing)
            counters["sources_added"] += merge_sources(existing["sources"], urls)
            counters["provider_refs_added"] += merge_provider_refs(existing["provider_refs"], refs)
    parse_extra_series_sources(vod, series, fichas, counters)
    for (title_key, year), item in series.items():
        meta = fichas.get(("s", title_key), {})
        item["tmdb_id"] = item.get("tmdb_id") or meta.get("tmdb_id")
        item["poster_url"] = item.get("poster_url") or meta.get("poster_path") or featured_posters.get(("s", title_key))
        item["genres"] = item.get("genres") or meta.get("genres", [])
        if item.get("subtype") not in {"anime", "dorama"}:
            item["subtype"] = "anime" if title_key in featured_anime or any("animação" in g.casefold() or "animation" in g.casefold() for g in item["genres"]) else (
                "dorama" if title_key in featured_doramas or "dorama" in title_key or "k-drama" in title_key else "series"
            )
        item["seasons"] = [item["seasons"][k] for k in sorted(item["seasons"], key=lambda x: int(x))]
        for season in item["seasons"]:
            season["episodes"].sort(key=lambda e: (e["episode"], e["audio"]))
    return series




def parse_extra_series_sources(vod: Path, series: dict, fichas: dict, counters: dict) -> None:
    files = (
        (vod / "mgeb" / "links-series.txt", "reference-mgeb", None),
        (vod / "redeflix" / "links-series.txt", "reference-redeflix", None),
        (vod / "redeflix" / "links-animes.txt", "reference-redeflix", "anime"),
        (vod / "redeflix" / "links-doramas.txt", "reference-redeflix", "dorama"),
    )
    by_tmdb = {}
    by_name = {}
    for item in series.values():
        meta = fichas.get(("s", norm(item.get("title", ""))), {})
        tmdb = item.get("tmdb_id") or meta.get("tmdb_id")
        if tmdb:
            by_tmdb[str(tmdb)] = item
        for name_key in {norm(item.get("title", "")), base_title(item.get("title", ""))}:
            if name_key:
                by_name.setdefault(name_key, []).append(item)

    for path, source_id, subtype in files:
        current = None
        for raw in read_lines(path) or ():
            line = raw.rstrip("\n")
            if not line:
                continue
            if line.startswith("@"):
                fields = line[1:].split("\t")
                title = fields[0].strip()
                year = fields[1].strip() if len(fields) > 1 and fields[1].strip().isdigit() else None
                tmdb_id = fields[2].strip() if len(fields) > 2 and fields[2].strip().isdigit() else None
                if not title:
                    current = None
                    continue
                key = (norm(title), year or "")
                current = by_tmdb.get(tmdb_id) if tmdb_id else None
                current = current or series.get(key)
                if current is None:
                    candidates = by_name.get(norm(title), []) or by_name.get(base_title(title), [])
                    current = next((item for item in candidates if not year or item.get("year") in (None, year)), None)
                if current is None:
                    current = {
                        "id": "series-" + slug(title) + ("-" + year if year else ""),
                        "title": title, "type": "series", "year": year, "tmdb_id": tmdb_id,
                        "poster_url": None, "genres": [], "subtype": subtype or "series",
                        "seasons": {}, "sources": [], "provider_refs": [],
                        "source_candidates_skipped": 0,
                    }
                    series[key] = current
                    for name_key in {norm(title), base_title(title)}:
                        if name_key:
                            by_name.setdefault(name_key, []).append(current)
                if year and not current.get("year"):
                    current["year"] = year
                if tmdb_id:
                    current["tmdb_id"] = current.get("tmdb_id") or tmdb_id
                    by_tmdb[tmdb_id] = current
                if subtype in {"anime", "dorama"}:
                    current["subtype"] = subtype
                continue

            if current is None:
                continue
            fields = line.split("\t")
            if len(fields) < 4 or not fields[0].isdigit() or not fields[1].isdigit():
                continue
            season_no, episode_no, audio = int(fields[0]), int(fields[1]), fields[2].strip().lower()
            urls, refs, skipped = split_sources(fields[3], audio, source_id=source_id, priority=20)
            counters["skipped_urls"] += skipped
            current["source_candidates_skipped"] = int(current.get("source_candidates_skipped", 0)) + skipped
            season = current.setdefault("seasons", {}).setdefault(
                str(season_no), {"season": season_no, "episodes": []}
            )
            episode_key = (episode_no, audio)
            existing = next((ep for ep in season["episodes"]
                             if (ep["episode"], ep["audio"]) == episode_key), None)
            if existing is None:
                existing = {"episode": episode_no, "audio": audio, "sources": [], "provider_refs": []}
                season["episodes"].append(existing)
            counters["sources_added"] += merge_sources(existing["sources"], urls)
            counters["provider_refs_added"] += merge_provider_refs(existing["provider_refs"], refs)


def merge_record(target: dict, incoming: dict) -> dict:
    """Merge metadata, source candidates and episodic structure without deleting old data."""
    for field in ("title", "type", "year", "tmdb_id", "poster_url", "subtype"):
        if field == "subtype" and incoming.get(field) in {"anime", "dorama"} and target.get(field) not in {"anime", "dorama"}:
            target[field] = incoming[field]
        elif not target.get(field) and incoming.get(field):
            target[field] = incoming[field]
    if not target.get("genres") and incoming.get("genres"):
        target["genres"] = list(incoming["genres"])
    target.setdefault("sources", [])
    target.setdefault("provider_refs", [])
    merge_sources(target["sources"], incoming.get("sources", []))
    merge_provider_refs(target["provider_refs"], incoming.get("provider_refs", []))
    target["source_candidates_skipped"] = max(
        int(target.get("source_candidates_skipped", 0)),
        int(incoming.get("source_candidates_skipped", 0)),
    )
    if incoming.get("seasons"):
        old_seasons = target.get("seasons", [])
        if isinstance(old_seasons, dict):
            old_seasons = list(old_seasons.values())
        season_map = {str(s.get("season")): s for s in old_seasons}
        for new_season in incoming["seasons"]:
            season_key = str(new_season.get("season"))
            season = season_map.get(season_key)
            if season is None:
                season = {"season": new_season.get("season"), "episodes": []}
                old_seasons.append(season)
                season_map[season_key] = season
            episode_map = {
                (int(e.get("episode", 0)), str(e.get("audio", ""))): e
                for e in season.setdefault("episodes", [])
            }
            for new_ep in new_season.get("episodes", []):
                ep_key = (int(new_ep.get("episode", 0)), str(new_ep.get("audio", "")))
                ep = episode_map.get(ep_key)
                if ep is None:
                    ep = {"episode": ep_key[0], "audio": ep_key[1], "sources": [], "provider_refs": []}
                    season["episodes"].append(ep)
                    episode_map[ep_key] = ep
                merge_sources(ep.setdefault("sources", []), new_ep.get("sources", []))
                merge_provider_refs(ep.setdefault("provider_refs", []), new_ep.get("provider_refs", []))
        old_seasons.sort(key=lambda s: int(s.get("season", 0)))
        for season in old_seasons:
            season["episodes"].sort(key=lambda e: (int(e.get("episode", 0)), str(e.get("audio", ""))))
        target["seasons"] = old_seasons
    return target


def load_existing_details(kind: str) -> dict[str, dict]:
    existing = {}
    folder = DETAILS / kind
    if folder.exists():
        for path in sorted(folder.glob("*.json")):
            try:
                records = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(records, list):
                for item in records:
                    if isinstance(item, dict) and item.get("id"):
                        ident = str(item["id"])
                        if ident in existing:
                            merge_record(existing[ident], item)
                        else:
                            existing[ident] = item
    previous_index = load_json(VOD_INDEX, {"movies": [], "series": [], "anime": [], "doramas": []})
    previous_items = previous_index.get(kind)
    if not isinstance(previous_items, list):
        category = previous_index.get("categories", {}).get(kind, {})
        index_path = category.get("index_path")
        previous_items = load_json(ROOT / index_path, []) if index_path else []
    for item in previous_items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        ident = str(item["id"])
        if ident not in existing:
            existing[ident] = {
                "id": ident, "title": item.get("title") or ident, "type": item.get("type") or kind,
                "year": item.get("year"), "tmdb_id": item.get("tmdb_id"),
                "poster_url": item.get("poster_url"), "genres": item.get("genres") or [],
                "subtype": item.get("subtype"), "sources": [], "provider_refs": [],
                "source_candidates_skipped": 0,
                **({"seasons": []} if kind in {"series", "anime", "doramas"} else {}),
            }
    return existing


def dedupe_records(items: list[dict]) -> list[dict]:
    by_id = {}
    for item in items:
        ident = str(item.get("id") or "")
        if not ident:
            continue
        if ident in by_id:
            merge_record(by_id[ident], item)
        else:
            by_id[ident] = item

    canonical = []
    by_tmdb = {}
    by_title_year = {}
    for item in by_id.values():
        tmdb_id = str(item.get("tmdb_id") or "").strip()
        year = str(item.get("year") or "")
        if not year:
            match = re.search(r"\\(((?:19|20)\\d{2})\\)\\s*$", str(item.get("title") or ""))
            year = match.group(1) if match else ""
        title_key = (base_title(item.get("title", "")), year)
        target = by_tmdb.get(tmdb_id) if tmdb_id else None
        if target is None:
            candidate = by_title_year.get(title_key)
            if candidate is not None:
                candidate_tmdb = str(candidate.get("tmdb_id") or "").strip()
                if not tmdb_id or not candidate_tmdb or candidate_tmdb == tmdb_id:
                    target = candidate
        if target is not None:
            merge_record(target, item)
            target_tmdb = str(target.get("tmdb_id") or "").strip()
            if target_tmdb:
                by_tmdb[target_tmdb] = target
            by_title_year.setdefault(title_key, target)
        else:
            canonical.append(item)
            if tmdb_id:
                by_tmdb[tmdb_id] = item
            by_title_year.setdefault(title_key, item)
    return canonical


def merge_catalog_records(kind: str, incoming: list[dict]) -> list[dict]:
    old = load_existing_details(kind)
    merged = dedupe_records(list(old.values()) + list(incoming))
    return sorted(merged, key=lambda x: (str(x.get("title", "")).casefold(), str(x.get("year") or "")))


def import_channels(reference: Path, current: dict, counters: dict) -> dict:
    vod_names = set()
    for line in read_lines(reference / "vod" / "busca.txt") or ():
        fields = line.rstrip("\n").split("\t")
        if len(fields) >= 2 and fields[1] in {"f", "s"}:
            title = fields[0].strip()
            vod_names.add(norm(title))
            vod_names.add(norm(re.sub(r"\s*\((?:19|20)\d{2}\)\s*$", "", title)))
            vod_names.add(norm(re.sub(r"\b(?:4k|uhd|fhd|hd|1080p|720p|sd)\b", "", title, flags=re.I)))
    channels = current.get("channels", [])
    before_channels = json.dumps(channels, ensure_ascii=False, sort_keys=True)
    by_name = {norm(c.get("name", "")): c for c in channels if c.get("name")}
    by_id = {c.get("id"): c for c in channels if c.get("id")}
    for path in (reference / "1.m3u", reference / "3.m3u"):
        name = None
        attrs = {}
        if not path.exists():
            continue
        for raw in read_lines(path) or ():
            line = raw.strip()
            if line.startswith("#EXTINF:"):
                # Parse attributes without splitting commas inside quotes.
                attrs = {k: v for k, v in re.findall(r'([\w-]+)="([^"]*)"', line)}
                quoted = False
                comma = -1
                for i, char in enumerate(line):
                    if char == '"':
                        quoted = not quoted
                    elif char == "," and not quoted:
                        comma = i
                        break
                name = line[comma + 1:].strip() if comma >= 0 else attrs.get("tvg-name")
            elif line and not line.startswith("#") and name:
                channel_name = (attrs.get("tvg-name") or name or "").strip()
                group_name = str(attrs.get("group-title") or "").casefold()
                is_vod_group = any(word in group_name for word in (
                    "filme", "movie", "série", "serie", "series", "anime", "dorama",
                    "novela", "temporada", "episodio", "episode", "vod",
                    "adulto", "adult", "xxx", "18+"
                ))
                is_episode_title = bool(re.search(r"\bS\d{1,2}\s*E\d{1,3}\b", channel_name, re.I))
                if not channel_name or is_vod_group or is_episode_title:
                    name, attrs = None, {}
                    continue
                key = norm(channel_name)
                source_path = urlsplit(line).path.lower() if line.lower().startswith(("http://", "https://")) else ""
                is_vod_url = bool(re.search(r"/(?:movie|series|vod|film|episode)/", source_path)) or bool(
                    re.search(r"\\.(?:mp4|mkv|avi|mov)$", source_path)
                )
                if key in vod_names or is_vod_url:
                    name, attrs = None, {}
                    continue
                target = by_name.get(key)
                source_is_safe = safe_candidate(line)
                if not source_is_safe:
                    counters["skipped_channel_urls"] += 1
                    if target is not None:
                        target["source_candidates_pending_review"] = int(target.get("source_candidates_pending_review", 0)) + 1
                    name, attrs = None, {}
                    continue
                if target is None:
                    target = {
                        "id": "ch-" + slug(channel_name), "name": channel_name,
                        "group": attrs.get("group-title") or "Outros",
                        "logo_url": attrs.get("tvg-logo") if safe_candidate(attrs.get("tvg-logo", "")) else None,
                        "epg_id": attrs.get("tvg-id") or None, "sources": [],
                        "stream_status": "imported", "source_candidates_pending_review": 0,
                    }
                    channels.append(target)
                    by_name[key] = target
                    by_id[target["id"]] = target
                    counters["channels_added"] += 1
                target.setdefault("sources", [])
                added = merge_sources(target["sources"], [{"url": line, "priority": 40, "source_id": SOURCE_ID}])
                counters["channel_sources_added"] += added
                if not target.get("logo_url") and safe_candidate(attrs.get("tvg-logo", "")):
                    target["logo_url"] = attrs["tvg-logo"]
                if not target.get("epg_id") and attrs.get("tvg-id"):
                    target["epg_id"] = attrs["tvg-id"]
                name, attrs = None, {}
    current["channels"] = channels
    if json.dumps(channels, ensure_ascii=False, sort_keys=True) != before_channels:
        current["generated_at"] = datetime.now(timezone.utc).isoformat()
    return current


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE)
    args = parser.parse_args()
    reference = args.reference_dir
    if not (reference / "vod").exists():
        raise SystemExit(f"Diretório de referência não encontrado: {reference / 'vod'}")

    counters = defaultdict(int)
    current_channels = load_json(CHANNELS_FILE, {"schema_version": 1, "channels": []})
    current_channels = import_channels(reference, current_channels, counters)
    write_json(CHANNELS_FILE, current_channels)

    fichas = read_fichas(reference / "vod" / "fichas.txt")
    featured_posters, featured_anime, featured_doramas = parse_featured(reference / "vod" / "destaques.txt")
    search_movies, search_series = parse_search_index(reference / "vod" / "busca.txt")
    movies = parse_movies(reference, fichas, featured_posters, counters, search_movies)
    movies = parse_extra_movie_sources(reference, movies, fichas, counters)
    series = parse_series(reference, fichas, featured_posters, featured_anime, featured_doramas, counters, search_series)

    # Títulos sem URL direta continuam no índice, e dados antigos nunca são removidos.
    movie_list = merge_catalog_records("movies", list(movies.values()))
    series_list = merge_catalog_records("series", list(series.values()))
    anime_list = merge_catalog_records("anime", [x for x in series_list if x.get("subtype") == "anime"])
    dorama_list = merge_catalog_records("doramas", [x for x in series_list if x.get("subtype") == "dorama"])

    detail_paths = {}
    written_detail_paths = set()
    for kind, items in (("movies", movie_list), ("series", series_list),
                        ("anime", anime_list), ("doramas", dorama_list)):
        groups = defaultdict(list)
        for item in items:
            groups[letter(item["title"])].append(item)
        chunk_size = {"movies": 100, "series": 60, "anime": 80, "doramas": 80}[kind]
        for initial, records in groups.items():
            for offset in range(0, len(records), chunk_size):
                chunk_no = offset // chunk_size
                chunk = records[offset:offset + chunk_size]
                relative_path = f"catalog/vod/details/{kind}/{initial}-{chunk_no:03d}.json"
                write_json_compact(ROOT / relative_path, chunk)
                written_detail_paths.add(relative_path)
                for item in chunk:
                    detail_paths[(kind, item["id"])] = relative_path

    def index_entry(item, kind):
        episode_sources = sum(
            len(ep.get("sources", []))
            for season in item.get("seasons", [])
            for ep in season.get("episodes", [])
        )
        episode_refs = sum(
            len(ep.get("provider_refs", []))
            for season in item.get("seasons", [])
            for ep in season.get("episodes", [])
        )
        detail_kind = {"movie": "movies", "dorama": "doramas"}.get(kind, kind)
        entry = {
            "id": item["id"],
            "title": item["title"],
            "type": item.get("type", kind),
            "detail_path": detail_paths[(detail_kind, item["id"])],
        }
        optional = {
            "year": item.get("year"),
            "tmdb_id": item.get("tmdb_id"),
            "poster_url": item.get("poster_url"),
            "genres": item.get("genres"),
            "subtype": item.get("subtype"),
        }
        for field, value in optional.items():
            if value not in (None, "", []):
                entry[field] = value
        source_count = len(item.get("sources", [])) + episode_sources
        provider_count = len(item.get("provider_refs", [])) + episode_refs
        if source_count:
            entry["source_count"] = source_count
        if provider_count:
            entry["provider_ref_count"] = provider_count
        return entry

    category_entries = {
        "movies": [index_entry(x, "movie") for x in movie_list],
        "series": [index_entry(x, "series") for x in series_list],
        "anime": [index_entry(x, "anime") for x in anime_list],
        "doramas": [index_entry(x, "dorama") for x in dorama_list],
    }
    category_index_changed = False
    category_manifest = {}
    for kind, entries in category_entries.items():
        relative_path = f"catalog/vod/index/{kind}.json"
        category_path = ROOT / relative_path
        previous_entries = load_json(category_path, [])
        if previous_entries != entries:
            category_index_changed = True
        write_json_compact(category_path, entries)
        category_manifest[kind] = {"count": len(entries), "index_path": relative_path}

    manifest = {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "categories": category_manifest,
    }
    previous_index = load_json(VOD_INDEX, {})
    previous_comparable = {k: v for k, v in previous_index.items() if k != "generated_at"}
    if previous_comparable == manifest and not category_index_changed:
        manifest["generated_at"] = previous_index.get("generated_at")
    else:
        manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_json_compact(VOD_INDEX, manifest)

    # Delete obsolete shards only after all replacement shards and indexes are published.
    # If index publication fails, old shard files remain available to the prior index.
    for kind in ("movies", "series", "anime", "doramas"):
        folder = DETAILS / kind
        if folder.exists():
            for old_path in folder.glob("*.json"):
                relative_path = old_path.relative_to(ROOT).as_posix()
                if relative_path not in written_detail_paths:
                    old_path.unlink()

    radios = load_json(RADIOS_FILE, {"schema_version": 1, "radios": []})
    known_radio = {norm(x.get("name", "")): x for x in radios.get("radios", [])}
    imported_radio_count = 0
    radio_file = reference / "vod" / "radios.txt"
    for line in read_lines(radio_file) or ():
        fields = line.rstrip("\n").split("|")
        if len(fields) < 3:
            continue
        radio_name = fields[1].strip()
        if not radio_name:
            continue
        key = norm(radio_name)
        if key in known_radio:
            continue
        stream = fields[2].strip()
        logo = fields[3].strip() if len(fields) > 3 and fields[3].strip() else None
        radio = {
            "id": "radio-" + slug(radio_name), "name": radio_name,
            "stream_url": stream if safe_candidate(stream) else None,
            "logo_url": logo if safe_candidate(logo or "") else None,
            "genre": None, "source_id": SOURCE_ID,
            "stream_status": "imported" if safe_candidate(stream) else "pending_review",
        }
        radios.setdefault("radios", []).append(radio)
        known_radio[key] = radio
        imported_radio_count += 1
    if imported_radio_count or not radios.get("generated_at"):
        radios["generated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(RADIOS_FILE, radios)

    counters["movies"] = len(movie_list)
    counters["series"] = len(series_list)
    counters["anime"] = len(anime_list)
    counters["doramas"] = len(dorama_list)
    counters["radios_added"] = imported_radio_count
    counters["channel_records_total"] = len(current_channels.get("channels", []))
    counters["radio_records_total"] = len(radios.get("radios", []))
    counters["fichas_matched"] = sum(bool(x.get("tmdb_id")) for x in movie_list + series_list)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "reference": "authorized-public-reference",
        "counts": dict(counters),
        "notes": [
            "Conteúdo adulto reservado não é importado.",
            "URLs com credenciais evidentes, tokens de consulta ou hosts privados são omitidas.",
            "Itens com IDs de provedores são preservados como referências para adaptadores futuros.",
            "A importação não testa reprodução durante a montagem do catálogo."
        ]
    }
    previous_report = load_json(REPORT, {})
    if any(previous_report.get(k) != v for k, v in report_data.items()) or not previous_report.get("generated_at"):
        report_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(REPORT, report_data)
    else:
        report_data["generated_at"] = previous_report["generated_at"]
    print("Importação CineHUB concluída: " + json.dumps(dict(counters), ensure_ascii=False))


if __name__ == "__main__":
    main()
