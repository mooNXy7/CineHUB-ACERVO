#!/usr/bin/env python3
"""Importa catálogo de canais e VOD do diretório de referência para o CineHUB ACERVO.

O processo é incremental e idempotente: preserva registros existentes, junta fontes
sem duplicar URLs e nunca publica URLs com credenciais evidentes ou hosts privados.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
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


def write_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_lines(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        yield from stream


def split_sources(text: str, audio: str = "dub") -> tuple[list[dict], list[dict], int]:
    urls, refs, skipped = [], [], 0
    for token in (text or "").split(","):
        token = token.strip()
        if not token:
            continue
        if token.lower().startswith(("http://", "https://")):
            clean = token.rstrip(".,;")
            if safe_candidate(clean):
                urls.append({"url": clean, "audio": audio, "priority": 50, "source_id": SOURCE_ID})
            else:
                skipped += 1
        elif re.match(r"^\d+:[A-Za-z0-9._/-]+$", token):
            provider, ident = token.split(":", 1)
            refs.append({"provider": provider, "ref": ident, "audio": audio, "source_id": SOURCE_ID})
    return urls, refs, skipped


def merge_sources(target: list[dict], incoming: list[dict]) -> int:
    known = {s.get("url") for s in target if isinstance(s, dict)}
    added = 0
    for source in incoming:
        url = source.get("url")
        if url and url not in known:
            target.append(source)
            known.add(url)
            added += 1
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
        if len(fields) >= 5 and fields[0] in {"f", "s"}:
            kind, title = fields[0], fields[1].strip()
            poster = fields[4].strip()
            if poster:
                posters[(kind, norm(title))] = poster if poster.startswith("http") else "https://image.tmdb.org/t/p/w342" + poster
            if kind == "s" and ("anime" in section or "anima" in section):
                anime.add(norm(title))
            if kind == "s" and ("dorama" in section or "drama asi" in section):
                doramas.add(norm(title))
    return posters, anime, doramas


def parse_movies(reference: Path, fichas: dict, featured_posters: dict, counters: dict) -> dict:
    movies = {}
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


def parse_series(reference: Path, fichas: dict, featured_posters: dict, featured_anime: set,
                 featured_doramas: set, counters: dict) -> dict:
    series = {}
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
            counters["sources_added"] += merge_sources(current["sources"], urls)
            counters["provider_refs_added"] += merge_provider_refs(current["provider_refs"], refs)
            season = current["seasons"].setdefault(str(season_no), {"season": season_no, "episodes": []})
            episode_key = (episode_no, audio)
            existing = next((e for e in season["episodes"] if (e["episode"], e["audio"]) == episode_key), None)
            if existing is None:
                existing = {"episode": episode_no, "audio": audio, "sources": [], "provider_refs": []}
                season["episodes"].append(existing)
            merge_sources(existing["sources"], urls)
            merge_provider_refs(existing["provider_refs"], refs)
    for (title_key, year), item in series.items():
        meta = fichas.get(("s", title_key), {})
        item["tmdb_id"] = meta.get("tmdb_id")
        item["poster_url"] = meta.get("poster_path") or featured_posters.get(("s", title_key))
        item["genres"] = meta.get("genres", [])
        item["subtype"] = "anime" if title_key in featured_anime or any("animação" in g.casefold() or "animation" in g.casefold() for g in item["genres"]) else (
            "dorama" if title_key in featured_doramas or "dorama" in title_key or "k-drama" in title_key else "series"
        )
        item["seasons"] = [item["seasons"][k] for k in sorted(item["seasons"], key=lambda x: int(x))]
        for season in item["seasons"]:
            season["episodes"].sort(key=lambda e: (e["episode"], e["audio"]))
    return series


def import_channels(reference: Path, current: dict, counters: dict) -> dict:
    channels = current.get("channels", [])
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
                name = line[comma + 1:].strip() if comma >= 0 else attrs.get("tvg-name")
            elif line and not line.startswith("#") and name:
                channel_name = (attrs.get("tvg-name") or name or "").strip()
                if not channel_name:
                    name, attrs = None, {}
                    continue
                key = norm(channel_name)
                target = by_name.get(key)
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
                if safe_candidate(line):
                    added = merge_sources(target["sources"], [{"url": line, "priority": 40, "source_id": SOURCE_ID}])
                    counters["channel_sources_added"] += added
                else:
                    target["source_candidates_pending_review"] = int(target.get("source_candidates_pending_review", 0)) + 1
                    counters["skipped_channel_urls"] += 1
                if not target.get("logo_url") and safe_candidate(attrs.get("tvg-logo", "")):
                    target["logo_url"] = attrs["tvg-logo"]
                if not target.get("epg_id") and attrs.get("tvg-id"):
                    target["epg_id"] = attrs["tvg-id"]
                name, attrs = None, {}
    current["channels"] = channels
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
    movies = parse_movies(reference, fichas, featured_posters, counters)
    series = parse_series(reference, fichas, featured_posters, featured_anime, featured_doramas, counters)

    # Títulos sem URL direta continuam no índice com identificadores de provedor:
    # os aplicativos podem resolver esses IDs por adaptadores sem perder o item.
    movie_list = sorted(movies.values(), key=lambda x: (x["title"].casefold(), x.get("year") or ""))
    series_list = sorted(series.values(), key=lambda x: (x["title"].casefold(), x.get("year") or ""))
    anime_list = [x for x in series_list if x.get("subtype") == "anime"]
    dorama_list = [x for x in series_list if x.get("subtype") == "dorama"]

    for kind, items in (("movies", movie_list), ("series", series_list),
                        ("anime", anime_list), ("doramas", dorama_list)):
        groups = defaultdict(list)
        for item in items:
            groups[letter(item["title"])].append(item)
        for initial, records in groups.items():
            write_json(DETAILS / kind / f"{initial}.json", records)

    def index_entry(item, kind):
        return {
            "id": item["id"], "title": item["title"], "year": item.get("year"),
            "tmdb_id": item.get("tmdb_id"), "poster_url": item.get("poster_url"),
            "genres": item.get("genres", []), "type": item.get("type", kind),
            "subtype": item.get("subtype"), "source_count": len(item.get("sources", [])),
            "provider_ref_count": len(item.get("provider_refs", [])),
            "detail_path": f"catalog/vod/details/{kind}/{letter(item['title'])}.json",
        }

    index = {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "movies": [index_entry(x, "movie") for x in movie_list],
        "series": [index_entry(x, "series") for x in series_list],
        "anime": [index_entry(x, "anime") for x in anime_list],
        "doramas": [index_entry(x, "dorama") for x in dorama_list],
    }
    write_json(VOD_INDEX, index)

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
    write_json(REPORT, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference": "authorized-public-reference",
        "counts": dict(counters),
        "notes": [
            "Conteúdo adulto reservado não é importado.",
            "URLs com credenciais evidentes, tokens de consulta ou hosts privados são omitidas.",
            "Itens com IDs de provedores são preservados como referências para adaptadores futuros.",
            "A importação não testa reprodução durante a montagem do catálogo."
        ]
    })
    print("Importação CineHUB concluída: " + json.dumps(dict(counters), ensure_ascii=False))


if __name__ == "__main__":
    main()
