#!/usr/bin/env python3
"""Refresh radio streams and fill missing radio metadata from authorized/public sources."""
from __future__ import annotations

import argparse
import json
from collections import Counter
import re
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    from .update_catalog import ROOT, fetch, safe_https_url, safe_source_url, atomic_write_json, normalize_key, SafeRedirectHandler
except ImportError:
    from update_catalog import ROOT, fetch, safe_https_url, safe_source_url, atomic_write_json, normalize_key, SafeRedirectHandler

MAX_SOURCE_RECORDS = 10000

# Only explicit, recognizable station tags are translated to a CineHUB genre.
GENRE_ALIASES = {
    "adult contemporary": "Adulto Contemporâneo",
    "alternative rock": "Rock Alternativo",
    "classic rock": "Rock",
    "hard rock": "Rock",
    "pop rock": "Pop/Rock",
    "sertanejo universitario": "Sertanejo",
    "bossa nova": "Bossa Nova",
    "top 40": "Pop",
    "news talk": "Jornalismo",
    "hip hop": "Hip-Hop",
    "electronic": "Eletrônica",
    "dance": "Eletrônica",
    "house": "Eletrônica",
    "techno": "Eletrônica",
    "trance": "Eletrônica",
    "pop": "Pop",
    "rock": "Rock",
    "sertanejo": "Sertanejo",
    "mpb": "MPB",
    "brazilian music": "MPB",
    "gospel": "Gospel",
    "christian": "Gospel",
    "religious": "Religiosa",
    "news": "Jornalismo",
    "talk": "Jornalismo",
    "journalism": "Jornalismo",
    "sports": "Esportes",
    "sport": "Esportes",
    "jazz": "Jazz",
    "blues": "Blues",
    "classical": "Clássica",
    "reggae": "Reggae",
    "samba": "Samba",
    "pagode": "Pagode",
    "forro": "Forró",
    "funk": "Funk",
    "rap": "Rap",
    "country": "Country",
    "flashback": "Flashback",
    "oldies": "Flashback",
    "80s": "Flashback",
    "90s": "Flashback",
    "regional": "Regional",
    "folk": "Regional",
    "latin": "Latina",
    "metal": "Metal",
    "alternative": "Alternativa",
    "alternative pop": "Indie",
    "indie": "Indie",
    "indie pop": "Indie",
    "indie rock": "Rock Alternativo",
    "dance pop": "Pop",
    "dance music": "Eletrônica",
    "edm": "Eletrônica",
    "electro": "Eletrônica",
    "disco": "Disco",
    "classic hits": "Flashback",
    "nostalgia": "Flashback",
    "2000s": "Flashback",
    "rock nacional": "Rock",
    "pop brasileiro": "Pop",
    "brazilian": "MPB",
    "musica brasileira": "MPB",
    "axe": "Axé",
    "arrocha": "Arrocha",
    "brega": "Brega",
    "funk carioca": "Funk",
    "funk brasileiro": "Funk",
    "louvor": "Gospel",
    "worship": "Gospel",
    "christian music": "Gospel",
    "evangelical": "Gospel",
    "evangelica": "Gospel",
    "catolica": "Religiosa",
    "religion": "Religiosa",
    "radio news": "Jornalismo",
    "news/talk": "Jornalismo",
    "noticias": "Jornalismo",
    "politics": "Jornalismo",
    "football": "Esportes",
    "soccer": "Esportes",
    "sports talk": "Esportes",
    "culture": "Cultura",
    "cultura": "Cultura",
    "educational": "Educativa",
    "education": "Educativa",
    "community": "Regional",
    "local": "Regional",
    "world music": "Música Mundial",
    "latin pop": "Latina",
    "latin music": "Latina",
    "instrumental": "Instrumental",
    "ambient": "Ambiental",
    "lounge": "Lounge",
    "easy listening": "Adulto Contemporâneo",
    "ecletica": "Eclética",
    "eclectic": "Eclética",
    "ecletico radioweb guarulhos": "Eclética",
    "misc": "Variedades",
    "mix": "Variedades",
    "multi": "Variedades",
    "hits": "Pop",
    "sertaneja": "Sertanejo",
    "futebol": "Esportes",
    "progressive rock": "Rock Alternativo",
    "gaucha": "Regional",
    "nativa": "Regional",
    "romanticas": "Romântica",
    "freestyle": "Eletrônica",
    "anime": "Anime",
    "jpop": "J-Pop",
    "jrock": "Rock",
    "pampa": "Regional",
    "brazil": "Música Brasileira",
    "anos80": "Flashback",
    "anos90": "Flashback",
    "anos 70": "Flashback",
    "flash back": "Flashback",
    "2000 s": "Flashback",
    "80 s": "Flashback",
    "90 s": "Flashback",
    "60 s": "Flashback",
    "70 s": "Flashback",
    "musica y noticias": "Jornalismo",
    "live sports": "Esportes",
    "local news": "Jornalismo",
    "sports news": "Esportes",
    "german": "Internacional",
    "tirol": "Regional",
    "jornalismo all news": "Jornalismo",
    "reggea": "Reggae",
    "entretenimiento": "Variedades",
    "entrevistas": "Jornalismo",
    "country music": "Country",
    "linhares": "Regional",
    "religiosa": "Religiosa",
    "sertanejo raiz": "Sertanejo",
    "varieties": "Variedades",
    "local music": "Regional",
    "local radio": "Regional",
    "radio universitaria": "Educativa",
    "university radio": "Educativa",
    "pop dance": "Pop",
    "brasil": "Música Brasileira",
    "soft": "Adulto Contemporâneo",
    "espiritismo": "Religiosa",
    "espiritual": "Religiosa",
    "radio espirita": "Religiosa",
}
GENRE_PRIORITY = [
    "Sertanejo", "MPB", "Gospel", "Jornalismo", "Esportes", "Pop/Rock",
    "Pop", "Rock Alternativo", "Rock", "Metal", "Eletrônica", "Flashback",
    "Jazz", "Blues", "Clássica", "Samba", "Pagode", "Forró", "Funk",
    "Hip-Hop", "Rap", "Reggae", "Bossa Nova", "Axé", "Forró", "Arrocha",
    "Brega", "Disco", "Indie", "Instrumental", "Ambiental", "Lounge",
    "Country", "Regional", "Latina", "Música Mundial", "Cultura", "Educativa",
    "Adulto Contemporâneo", "Alternativa", "Religiosa", "Eclética",
    "Romântica", "J-Pop", "Anime", "Música Brasileira", "Internacional", "Variedades",
]


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "radio"


def normalize_station_name(value: str) -> str:
    value = normalize_key(value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = value.split()
    while tokens and tokens[-1] in {"fm", "am", "web", "online"}:
        tokens.pop()
    return " ".join(tokens)


def normalize_stream_url(value: str) -> str:
    value = str(value or "").strip()
    if not safe_https_url(value):
        return ""
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host if port in (None, 443) else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit(("https", netloc, path, parsed.query, ""))



def fetch_radio_source(url: str, attempts: int = 3) -> str:
    """Retry transient upstream resets without weakening URL validation."""
    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            return fetch(url)
        except urllib.error.HTTPError as exc:
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                raise
            last_error = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
        if attempt + 1 < max(1, attempts):
            time.sleep(1.5 * (2 ** attempt))
    assert last_error is not None
    raise last_error


def parse_radio_source(text: str, source_id: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    counts = {"lines_seen": 0, "accepted": 0, "malformed": 0, "unsafe_streams": 0,
              "ambiguous_names": 0}
    seen: dict[str, str] = {}
    ambiguous_names: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        counts["lines_seen"] += 1
        if "|" not in line:
            counts["malformed"] += 1
            continue
        name, stream_url = (part.strip() for part in line.split("|", 1))
        if not name or not stream_url:
            counts["malformed"] += 1
            continue
        if not safe_https_url(stream_url):
            counts["unsafe_streams"] += 1
            continue
        key = normalize_station_name(name)
        if key in ambiguous_names:
            continue
        if key in seen:
            if seen[key] == stream_url:
                continue
            records = [record for record in records if normalize_station_name(record["name"]) != key]
            seen.pop(key, None)
            ambiguous_names.add(key)
            counts["accepted"] = max(0, counts["accepted"] - 1)
            counts["ambiguous_names"] += 1
            continue
        seen[key] = stream_url
        records.append({
            "id": "radio." + slug(name),
            "name": name,
            "stream_url": stream_url,
            "logo_url": None,
            "genre": None,
            "source_id": source_id,
        })
        counts["accepted"] += 1
        if len(records) > MAX_SOURCE_RECORDS:
            raise ValueError(f"radio source exceeds {MAX_SOURCE_RECORDS} records")
    return records, counts


def parse_radio_browser_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Radio Browser API response must be a JSON array")
    stations = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if str(item.get("countrycode") or "").upper() != "BR":
            continue
        if item.get("lastcheckok") not in (1, True, "1"):
            continue
        if not str(item.get("name") or "").strip():
            continue
        stations.append(item)
        if len(stations) > MAX_SOURCE_RECORDS:
            raise ValueError(f"Radio Browser source exceeds {MAX_SOURCE_RECORDS} stations")
    return stations


def genre_from_tags(tags: Any) -> str | None:
    if isinstance(tags, list):
        raw_tags = tags
    else:
        raw_tags = str(tags or "").split(",")
    found: list[str] = []
    for raw in raw_tags:
        tag = normalize_key(raw)
        tag = re.sub(r"[^a-z0-9]+", " ", tag).strip()
        if tag in GENRE_ALIASES:
            genre = GENRE_ALIASES[tag]
            if genre not in found:
                found.append(genre)
    for genre in GENRE_PRIORITY:
        if genre in found:
            return genre
    return found[0] if found else None


@lru_cache(maxsize=256)
def probe_homepage_favicon(homepage: str) -> str | None:
    """Accept only an image favicon served over HTTPS by the station's own homepage host."""
    if not safe_https_url(homepage):
        return None
    parsed = urlsplit(homepage)
    homepage_host = (parsed.hostname or "").lower()
    if not homepage_host:
        return None
    candidate = urlunsplit((parsed.scheme, parsed.netloc, "/favicon.ico", "", ""))
    request = urllib.request.Request(
        candidate,
        headers={"User-Agent": "CineHUB-ACERVO/0.2 (+radio metadata)", "Accept": "image/*"},
    )
    opener = urllib.request.build_opener(SafeRedirectHandler())
    try:
        with opener.open(request, timeout=3) as response:
            final_url = response.geturl()
            final_host = (urlsplit(final_url).hostname or "").lower()
            if not safe_https_url(final_url) or final_host != homepage_host:
                return None
            if not 200 <= int(getattr(response, "status", 200)) < 300:
                return None
            content_type = str(response.headers.get("Content-Type", "")).lower()
            sample = response.read(1024)
            image_signature = (
                sample.startswith(b"\x00\x00\x01\x00")
                or sample.startswith(b"\x89PNG")
                or sample.startswith(b"\xff\xd8")
                or sample.startswith((b"GIF87a", b"GIF89a"))
                or (sample.startswith(b"RIFF") and b"WEBP" in sample[:16])
                or b"<svg" in sample[:512].lower()
            )
            if not content_type.startswith("image/") and not image_signature:
                return None
            if not image_signature and not content_type.startswith("image/"):
                return None
            return candidate
    except (OSError, ValueError, urllib.error.URLError):
        return None


def safe_station_favicon(station: dict[str, Any]) -> str | None:
    favicon = str(station.get("favicon") or "").strip()
    homepage = str(station.get("homepage") or "").strip()
    if safe_https_url(favicon) and safe_https_url(homepage):
        favicon_host = (urlsplit(favicon).hostname or "").lower()
        homepage_host = (urlsplit(homepage).hostname or "").lower()
        blocked = {"google.com", "googleusercontent.com", "favicon.io", "faviconkit.com",
                   "duckduckgo.com", "gravatar.com", "cloudflare.com"}
        same_host = (
            favicon_host == homepage_host
            or favicon_host.endswith("." + homepage_host)
            or homepage_host.endswith("." + favicon_host)
        )
        is_blocked = any(favicon_host == host or favicon_host.endswith("." + host) for host in blocked)
        if favicon_host and homepage_host and same_host and not is_blocked:
            return favicon
    return probe_homepage_favicon(homepage)


def match_radio_browser_station(radio: dict[str, Any], stations: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    name_key = normalize_station_name(str(radio.get("name") or ""))
    stream_key = normalize_stream_url(str(radio.get("stream_url") or ""))

    # An exact stream URL is the strongest identity signal. Do not require the
    # station display name to match first: Radio Browser commonly uses a legal
    # or abbreviated brand while the catalog uses the local on-air name.
    # Radio Browser payloads are already restricted to healthy Brazilian stations.
    candidates: dict[str, dict[str, Any]] = {}
    if stream_key:
        for station in stations:
            station_urls = {
                normalize_stream_url(str(station.get("url") or "")),
                normalize_stream_url(str(station.get("url_resolved") or "")),
            }
            station_urls.discard("")
            station_id = str(station.get("stationuuid") or station.get("url") or station.get("name"))
            if stream_key in station_urls:
                candidates[station_id] = station
    if len(candidates) == 1:
        return next(iter(candidates.values())), "exact_stream"
    if len(candidates) > 1:
        return None, "ambiguous_stream"

    # Name-only fallback remains deliberately strict: one exact normalized
    # station name must identify exactly one healthy Brazilian station.
    by_name = [station for station in stations
               if normalize_station_name(str(station.get("name") or "")) == name_key]
    if len(by_name) == 1:
        return by_name[0], "exact_name"
    if len(by_name) > 1:
        return None, "ambiguous_name"
    return None, "unmatched"


def apply_radio_browser_metadata(radios: list[dict[str, Any]], stations: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "matched_by_stream": 0, "matched_by_name": 0, "unmatched": 0,
        "ambiguous": 0, "genres_filled": 0, "logos_filled": 0,
        "favicon_rejected": 0, "homepage_favicon_filled": 0, "genre_unclassified": 0,
        "unclassified_tags": {},
        "updated_radio_names": [],
    }
    unclassified_tags: Counter[str] = Counter()
    matched: list[tuple[dict[str, Any], dict[str, Any] | None, str]] = []
    stations_to_probe: dict[str, dict[str, Any]] = {}

    # Resolve identities once, then probe official homepages concurrently. This
    # keeps slow favicon hosts from serially blocking the full radio refresh.
    for radio in radios:
        station, method = match_radio_browser_station(radio, stations)
        matched.append((radio, station, method))
        if station and not str(radio.get("logo_url") or "").strip():
            station_key = str(
                station.get("stationuuid")
                or station.get("url_resolved")
                or station.get("url")
                or station.get("name")
            )
            stations_to_probe.setdefault(station_key, station)

    probe_items = list(stations_to_probe.items())
    with ThreadPoolExecutor(max_workers=8) as executor:
        probe_results = list(executor.map(
            safe_station_favicon,
            [station for _, station in probe_items],
        ))
    favicon_by_station = {
        station_key: favicon
        for (station_key, _), favicon in zip(probe_items, probe_results)
    }

    for radio, station, method in matched:
        if not station:
            if method.startswith("ambiguous"):
                counts["ambiguous"] += 1
            else:
                counts["unmatched"] += 1
            continue
        if method.startswith("exact_stream"):
            counts["matched_by_stream"] += 1
        else:
            counts["matched_by_name"] += 1

        changed = False
        if not str(radio.get("genre") or "").strip():
            genre = genre_from_tags(station.get("tags"))
            if genre:
                radio["genre"] = genre
                counts["genres_filled"] += 1
                changed = True
            else:
                counts["genre_unclassified"] += 1
                for tag in str(station.get("tags") or "").split(","):
                    normalized_tag = normalize_key(tag)
                    if normalized_tag:
                        unclassified_tags[normalized_tag] += 1

        if not str(radio.get("logo_url") or "").strip():
            station_key = str(
                station.get("stationuuid")
                or station.get("url_resolved")
                or station.get("url")
                or station.get("name")
            )
            favicon = favicon_by_station.get(station_key)
            if favicon:
                radio["logo_url"] = favicon
                counts["logos_filled"] += 1
                if favicon != str(station.get("favicon") or "").strip():
                    counts["homepage_favicon_filled"] += 1
                changed = True
            elif station.get("favicon"):
                counts["favicon_rejected"] += 1

        if changed and len(counts["updated_radio_names"]) < 100:
            counts["updated_radio_names"].append(str(radio.get("name") or ""))
    counts["unclassified_tags"] = dict(unclassified_tags.most_common(50))
    return counts

def merge_radio_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = [dict(item) for item in existing if isinstance(item, dict)]
    by_id: dict[str, list[dict[str, Any]]] = {}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in result:
        if item.get("id"):
            by_id.setdefault(str(item["id"]), []).append(item)
        if item.get("name"):
            by_name.setdefault(normalize_station_name(item["name"]), []).append(item)

    added = filled_stream = unchanged = conflicts = ambiguous = 0
    conflict_names: list[str] = []
    for item in incoming:
        id_matches = by_id.get(str(item.get("id") or ""), [])
        name_matches = by_name.get(normalize_station_name(item.get("name")), [])
        matches = id_matches or name_matches
        if len(matches) > 1:
            ambiguous += 1
            continue
        if not matches:
            clone = dict(item)
            result.append(clone)
            by_id.setdefault(str(clone.get("id")), []).append(clone)
            by_name.setdefault(normalize_station_name(clone.get("name")), []).append(clone)
            added += 1
            continue

        target = matches[0]
        current_url = str(target.get("stream_url") or "").strip()
        candidate_url = str(item.get("stream_url") or "").strip()
        if not current_url and candidate_url:
            target["stream_url"] = candidate_url
            if not target.get("source_id"):
                target["source_id"] = item.get("source_id")
            filled_stream += 1
        elif current_url == candidate_url:
            unchanged += 1
        elif current_url and candidate_url:
            conflicts += 1
            if len(conflict_names) < 100:
                conflict_names.append(str(target.get("name") or item.get("name") or ""))

        # Only fill missing descriptive fields. Never overwrite existing logos/genres.
        for field in ("logo_url", "genre"):
            if not target.get(field) and item.get(field):
                target[field] = item[field]

    return result, {
        "added": added,
        "filled_stream": filled_stream,
        "unchanged": unchanged,
        "stream_conflicts": conflicts,
        "ambiguous_matches": ambiguous,
        "stream_conflict_names": conflict_names,
    }


def update(root: Path = ROOT) -> dict[str, Any]:
    sources_path = root / "sources/sources.json"
    out_path = root / "catalog/radios/radios.json"
    cfg = json.loads(sources_path.read_text(encoding="utf-8"))
    current = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {
        "schema_version": 1, "radios": []
    }
    if not isinstance(current, dict) or not isinstance(current.get("radios"), list):
        raise ValueError("catalog/radios/radios.json must contain a radios array")

    active = [s for s in cfg.get("sources", [])
              if isinstance(s, dict) and s.get("enabled") and s.get("category") == "radio"]
    collected: list[dict[str, Any]] = []
    radio_browser_stations: list[dict[str, Any]] = []
    failures: list[str] = []
    source_counts: list[dict[str, Any]] = []
    for source in sorted(active, key=lambda item: item.get("priority", 999)):
        source_id = str(source.get("id") or "")
        url = str(source.get("url") or "")
        if not safe_source_url(url):
            failures.append(f"{source_id or '?'}: URL HTTPS ausente/inválida")
            continue
        try:
            body = fetch_radio_source(url)
            if source.get("format") == "pipe-delimited":
                parsed, counts = parse_radio_source(body, source_id)
                if not parsed:
                    raise ValueError("nenhuma rádio com nome e stream HTTPS seguro")
                source_counts.append({"source_id": source_id, **counts})
                collected.extend(parsed)
            elif source.get("format") == "radio-browser-json":
                stations = parse_radio_browser_payload(json.loads(body))
                if not stations:
                    raise ValueError("Radio Browser não retornou estações brasileiras válidas")
                radio_browser_stations.extend(stations)
                source_counts.append({"source_id": source_id, "stations": len(stations)})
            else:
                failures.append(f"{source_id or '?'}: formato não suportado")
        except Exception as exc:
            failures.append(f"{source_id or '?'}: {type(exc).__name__}: {exc}")

    if active and failures and not collected and not radio_browser_stations:
        raise RuntimeError("Nenhuma fonte de rádio segura válida; catálogo anterior preservado: " + "; ".join(failures))

    original_radios = [dict(item) for item in current["radios"] if isinstance(item, dict)]
    # Always clone before applying metadata so a Radio Browser-only fallback is
    # still detected as a catalog mutation when the stream-reference fetch fails.
    merged, merge_counts = merge_radio_records(original_radios, collected)
    metadata_counts = apply_radio_browser_metadata(merged, radio_browser_stations) if radio_browser_stations else {
        "matched_by_stream": 0, "matched_by_name": 0, "unmatched": 0, "ambiguous": 0,
        "genres_filled": 0, "logos_filled": 0, "favicon_rejected": 0,
        "genre_unclassified": 0, "unclassified_tags": {}, "updated_radio_names": [],
    }
    catalog_mutated = merged != original_radios
    if catalog_mutated:
        current["radios"] = merged
        current["generated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(out_path, current)

    report = {
        "schema_version": 1,
        "report_type": "radio_source_refresh",
        "catalog_mutated": catalog_mutated,
        "active_sources": len(active),
        "sources": source_counts,
        "merge": merge_counts,
        "radio_browser_metadata": metadata_counts,
        "failures": failures,
        "safety": [
            "Only names and HTTPS streams are read from the authorized SaimoPlayer reference.",
            "Radio Browser public-domain metadata is matched by exact normalized name and/or exact stream URL.",
            "Only recognized tags fill missing genres; existing genres are never overwritten.",
            "Only HTTPS favicons hosted on the station homepage domain fill missing logos; existing logos are never overwritten.",
            "Streams, IDs, playback settings, headers, credentials, and DRM are never replaced or imported from Radio Browser.",
            "Ambiguous station matches and untrusted favicon hosts are skipped for review.",
        ],
    }
    report_path = root / "reports/radio-source-refresh.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "failures"}, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    update(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
