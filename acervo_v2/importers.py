from __future__ import annotations

import hashlib
import io
import json
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

PARSER_VERSION = "1.0.0"
SENSITIVE_QUERY_KEYS = {"token", "access_token", "auth", "authorization", "password", "passwd",
                        "username", "user", "key", "signature", "sig", "session", "expires"}


def normalize_name(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\b(?:4k|uhd|fhd|hd|1080p|720p|sd|br)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def stable_id(domain: str, source_id: str, stable_key: str) -> str:
    key = str(stable_key or "").strip()
    if not key:
        raise ValueError("stable_key is required to derive a deterministic ID")
    digest = hashlib.sha256((domain + "\0" + source_id + "\0" + key).encode("utf-8")).hexdigest()[:24]
    return domain.rstrip("s") + "." + digest


def input_provenance(source_id: str, method: str, payload: bytes | str,
                     source_ref: str | None = None, confidence: float = 1.0) -> dict:
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    return {
        "source_id": source_id,
        "source_ref": source_ref,
        "method": method,
        "parser_version": PARSER_VERSION,
        "collected_at": (datetime.fromtimestamp(int(os.environ["SOURCE_DATE_EPOCH"]), timezone.utc)
                         .replace(microsecond=0).isoformat().replace("+00:00", "Z")
                         if os.environ.get("SOURCE_DATE_EPOCH", "").isdigit() else None),
        "collection_time_known": os.environ.get("SOURCE_DATE_EPOCH", "").isdigit(),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "confidence": confidence,
    }


def safe_stream_url(value: object, allow_http: bool = True) -> tuple[bool, str]:
    try:
        parsed = urlsplit(str(value or "").strip())
        allowed = {"https", "http"} if allow_http else {"https"}
        if parsed.scheme.lower() not in allowed or not parsed.hostname:
            return False, "unsupported_or_missing_scheme"
        if parsed.username is not None or parsed.password is not None:
            return False, "embedded_credentials"
        if any(key.lower() in SENSITIVE_QUERY_KEYS for key, _ in parse_qsl(parsed.query)):
            return False, "sensitive_query_parameter"
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False, "local_host"
        return True, "ok"
    except (TypeError, ValueError):
        return False, "invalid_url"


def is_image_url(value: object) -> bool:
    try:
        path = urlsplit(str(value or "").strip()).path.lower()
    except ValueError:
        return False
    return bool(re.search(r"\.(?:png|jpe?g|webp|gif|svg|ico|avif)(?:$|/)", path))


def _stream_variant(item: dict, entity_id: str, source_id: str, provenance: dict,
                    quarantine: list, domain: str = "stream") -> dict | None:
    url = str(item.get("url") or item.get("stream_url") or "").strip()
    ok, reason = safe_stream_url(url)
    if not ok:
        quarantine.append({"domain": domain, "reason": reason, "entity_id": entity_id,
                           "source_id": source_id, "raw": item})
        return None
    if domain == "radio" and is_image_url(url):
        quarantine.append({"domain": domain, "reason": "image_url_in_audio_stream", "entity_id": entity_id,
                           "source_id": source_id, "raw": item})
        return None
    variant_source = str(item.get("source_id") or source_id)
    try:
        priority = int(item.get("priority", 100) or 100)
    except (TypeError, ValueError):
        priority = 100
    status = str(item.get("status") or "unverified")
    if status not in {"unverified", "imported", "validated", "reachable", "unavailable", "quarantined", "unknown"}:
        status = "unknown"
    return {
        "id": str(item.get("id") or stable_id("stream", variant_source, url + "|" + str(item.get("audio") or ""))),
        "entity_id": entity_id,
        "source_id": variant_source,
        "url": url,
        "protocol": urlsplit(url).scheme.lower(),
        "priority": priority,
        "audio": item.get("audio"),
        "status": status,
        "provenance": [provenance],
        "raw": item,
    }


def _record_id(domain: str, item: dict, source_id: str, key: str) -> str:
    return str(item.get("id") or stable_id(domain, source_id, str(item.get(key) or key)))


def _unique_variants(streams: list[dict]) -> list[dict]:
    result, seen = [], set()
    for stream in streams:
        key = (stream.get("source_id"), stream.get("url"), stream.get("audio"))
        if key not in seen:
            seen.add(key)
            result.append(stream)
    return result


def parse_channels_json(document: dict, source_id: str = "catalog-existing",
                        source_ref: str = "catalog/channels/channels.json") -> tuple[list, list]:
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True)
    prov = input_provenance(source_id, "channels-json", payload, source_ref)
    records, quarantine = [], []
    for item in document.get("channels", []) if isinstance(document, dict) else []:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            quarantine.append({"domain": "channels", "reason": "missing_name", "raw": item})
            continue
        ident = _record_id("channel", item, source_id, "name")
        sources = item.get("sources") if isinstance(item.get("sources"), list) else []
        streams = _unique_variants([x for raw in sources if isinstance(raw, dict)
                   if (x := _stream_variant(raw, ident, source_id, prov, quarantine))])
        records.append({
            "id": ident, "name": str(item["name"]).strip(),
            "aliases": item.get("aliases", []) if isinstance(item.get("aliases"), list) else [],
            "group": item.get("group"), "country": item.get("country"), "language": item.get("language"),
            "logo_url": item.get("logo_url") if item.get("logo_url") and safe_stream_url(item.get("logo_url"))[0] else None, "epg_id": item.get("epg_id"),
            "epg_sources": item.get("epg_sources", []), "streams": streams,
            "provenance": [prov], "raw": item,
        })
    return records, quarantine


def _split_extinf(line: str) -> tuple[str, str]:
    quoted = False
    for index, char in enumerate(line):
        if char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            return line[:index], line[index + 1:].strip()
    return line, ""


def parse_m3u(text: str, source_id: str, source_ref: str = "input.m3u",
               priority: int = 100) -> tuple[list, list]:
    prov = input_provenance(source_id, "m3u", text, source_ref)
    records, quarantine = [], []
    name = None
    attrs = {}
    raw_extinf = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#EXTINF:"):
            header, name = _split_extinf(line)
            attrs = {k: v for k, v in re.findall(r'([\w-]+)="([^"]*)"', header)}
            name = name or attrs.get("tvg-name")
            raw_extinf = line
        elif line and not line.startswith("#") and name:
            title = str(attrs.get("tvg-name") or name).strip()
            if not title:
                quarantine.append({"domain": "channels", "reason": "missing_name", "raw": line})
                name, attrs = None, {}
                continue
            ident = stable_id("channel", source_id, attrs.get("tvg-id") or normalize_name(title))
            stream = _stream_variant({"url": line, "priority": priority, "source_id": source_id},
                                     ident, source_id, prov, quarantine)
            records.append({
                "id": ident, "name": title, "aliases": [],
                "group": attrs.get("group-title") or "Outros",
                "logo_url": (attrs.get("tvg-logo") or None) if attrs.get("tvg-logo") and safe_stream_url(attrs.get("tvg-logo"))[0] else None, "epg_id": attrs.get("tvg-id"),
                "streams": [stream] if stream else [], "provenance": [prov],
                "raw": {"extinf": raw_extinf, "attributes": attrs, "stream_line": line},
            })
            name, attrs, raw_extinf = None, {}, None
    return records, quarantine


def parse_radio_line(line: str) -> dict | None:
    fields = str(line or "").rstrip("\r\n").split("|")
    if len(fields) == 2:
        name, stream = fields
        logo = None
        legacy_id = None
    elif len(fields) >= 3:
        legacy_id, name, stream = fields[:3]
        logo = fields[3] if len(fields) > 3 and fields[3].strip() else None
    else:
        return None
    name, stream = str(name).strip(), str(stream).strip()
    if not name:
        return None
    return {"id": legacy_id.strip() if legacy_id else None, "name": name,
            "stream_url": stream or None, "logo_url": logo.strip() if logo else None,
            "raw_line": line}


def parse_radios_text(text: str, source_id: str, source_ref: str = "radios.txt") -> tuple[list, list]:
    prov = input_provenance(source_id, "pipe-delimited-radio-list", text, source_ref)
    records, quarantine = [], []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = parse_radio_line(line)
        if not item:
            quarantine.append({"domain": "radios", "reason": "invalid_row", "line": line_number, "raw": line})
            continue
        ident = str(item.get("id") or stable_id("radio", source_id, normalize_name(item["name"])))
        stream = item.get("stream_url")
        streams = []
        if stream:
            variant = _stream_variant({"url": stream, "source_id": source_id}, ident, source_id,
                                      prov, quarantine, domain="radio")
            if variant:
                streams.append(variant)
        logo = item.get("logo_url")
        if logo and not safe_stream_url(logo)[0]:
            quarantine.append({"domain": "logos", "reason": "invalid_logo_url", "entity_id": ident, "raw": logo})
            logo = None
        records.append({"id": ident, "name": item["name"], "aliases": [], "genre": None,
                        "country": None, "language": None, "logo_url": logo,
                        "streams": streams, "provenance": [prov], "raw": item})
    return records, quarantine


def parse_radios_json(document: dict, source_id: str = "catalog-existing",
                      source_ref: str = "catalog/radios/radios.json") -> tuple[list, list]:
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True)
    prov = input_provenance(source_id, "radios-json", payload, source_ref)
    records, quarantine = [], []
    for item in document.get("radios", []) if isinstance(document, dict) else []:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            quarantine.append({"domain": "radios", "reason": "missing_name", "raw": item})
            continue
        ident = _record_id("radio", item, source_id, "name")
        raw_streams = list(item.get("streams", [])) if isinstance(item.get("streams"), list) else []
        if item.get("stream_url"):
            raw_streams.append({"url": item["stream_url"], "source_id": item.get("source_id") or source_id})
        streams = []
        seen = set()
        for raw in raw_streams:
            if not isinstance(raw, dict):
                continue
            url = str(raw.get("url") or raw.get("stream_url") or "").strip()
            variant_key = (url, raw.get("audio"), raw.get("source_id"))
            if variant_key in seen:
                continue
            seen.add(variant_key)
            variant = _stream_variant(raw, ident, source_id, prov, quarantine, domain="radio")
            if variant:
                streams.append(variant)
        records.append({"id": ident, "name": str(item["name"]).strip(),
                        "aliases": item.get("aliases", []) if isinstance(item.get("aliases"), list) else [],
                        "genre": item.get("genre"), "country": item.get("country"),
                        "language": item.get("language"), "logo_url": item.get("logo_url") if item.get("logo_url") and safe_stream_url(item.get("logo_url"))[0] else None,
                        "streams": streams, "provenance": [prov], "raw": item})
    return records, quarantine


def _reference_sources(value: str, entity_id: str, source_id: str, prov: dict,
                       quarantine: list, domain: str) -> tuple[list, list]:
    streams, refs = [], []
    for token in (value or "").split(","):
        token = token.strip()
        if not token:
            continue
        if token.lower().startswith(("http://", "https://")):
            variant = _stream_variant({"url": token, "source_id": source_id}, entity_id,
                                      source_id, prov, quarantine, domain=domain)
            if variant:
                streams.append(variant)
        elif re.match(r"^\d+:[A-Za-z0-9._/?=&%+-]+$", token):
            provider, ref = token.split(":", 1)
            refs.append({"provider": provider, "ref": ref, "source_id": source_id})
        else:
            quarantine.append({"domain": domain, "reason": "unrecognized_source_token",
                               "entity_id": entity_id, "raw": token})
    return streams, refs


def parse_vod_reference_movies(text: str, source_id: str, source_ref: str = "vod/filmes-*.txt") -> tuple[list, list]:
    prov = input_provenance(source_id, "vod-reference-movie-lines", text, source_ref)
    records, quarantine, by_key = [], [], {}
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#") or "\t" not in line:
            continue
        fields = line.split("\t")
        title = fields[0].strip()
        if not title:
            quarantine.append({"domain": "vod", "reason": "missing_title", "line": line_no, "raw": line})
            continue
        year_match = re.search(r"\(((?:19|20)\d{2})\)\s*$", title)
        key = normalize_name(title)
        record = by_key.get(key)
        if record is None:
            ident = stable_id("vod", source_id, "movie:" + key)
            record = {"id": ident, "type": "movie", "title": title,
                      "year": year_match.group(1) if year_match else None,
                      "external_ids": {}, "genres": [], "sources": [], "provider_refs": [],
                      "seasons": [], "provenance": [prov], "raw": {"reference_lines": []}}
            by_key[key] = record
            records.append(record)
        record["raw"]["reference_lines"].append(line)
        for field in fields[1:]:
            if "=" not in field:
                continue
            audio, value = field.split("=", 1)
            if audio not in {"dub", "leg", "legendado", "dublado"}:
                continue
            streams, refs = _reference_sources(value, record["id"], source_id, prov, quarantine, "vod")
            for stream in streams:
                stream["audio"] = audio
                stream["id"] = stable_id("stream", source_id, stream["url"] + "|" + audio)
                if all((x["url"], x.get("audio")) != (stream["url"], audio) for x in record["sources"]):
                    record["sources"].append(stream)
            record["provider_refs"].extend(x for x in refs if x not in record["provider_refs"])
    return records, quarantine


def parse_vod_reference_series(text: str, source_id: str, source_ref: str = "vod/series-*.txt") -> tuple[list, list]:
    prov = input_provenance(source_id, "vod-reference-series-lines", text, source_ref)
    records, quarantine, by_key = [], [], {}
    current = None
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if line.startswith("@"):
            fields = line[1:].split("\t")
            title = fields[0].strip()
            year = fields[1].strip() if len(fields) > 1 and re.fullmatch(r"(?:19|20)\d{2}", fields[1].strip()) else None
            if not title:
                current = None
                quarantine.append({"domain": "vod", "reason": "missing_series_title", "line": line_no, "raw": line})
                continue
            key = normalize_name(title) + "|" + (year or "")
            current = by_key.get(key)
            if current is None:
                current = {"id": stable_id("vod", source_id, "series:" + key),
                           "type": "series", "title": title, "year": year,
                           "external_ids": {}, "genres": [], "sources": [], "provider_refs": [],
                           "seasons": [], "provenance": [prov], "raw": {"reference_lines": []}}
                by_key[key] = current
                records.append(current)
            current["raw"]["reference_lines"].append(line)
            continue
        if current is None:
            quarantine.append({"domain": "vod", "reason": "episode_without_series_header",
                               "line": line_no, "raw": line})
            continue
        fields = line.split("\t")
        if len(fields) < 4 or not fields[0].isdigit() or not fields[1].isdigit():
            quarantine.append({"domain": "vod", "reason": "invalid_episode_row", "line": line_no, "raw": line})
            continue
        season_no, episode_no, audio = int(fields[0]), int(fields[1]), fields[2].strip().lower()
        season = next((x for x in current["seasons"] if x["season"] == season_no), None)
        if season is None:
            season = {"season": season_no, "episodes": []}
            current["seasons"].append(season)
        episode = next((x for x in season["episodes"] if x["episode"] == episode_no and x["audio"] == audio), None)
        if episode is None:
            episode = {"episode": episode_no, "audio": audio, "sources": [], "provider_refs": []}
            season["episodes"].append(episode)
        streams, refs = _reference_sources(fields[3], current["id"], source_id, prov, quarantine, "vod")
        for stream in streams:
            stream["audio"] = audio
            stream["id"] = stable_id("stream", source_id, stream["url"] + "|" + audio)
            if all((x["url"], x.get("audio")) != (stream["url"], audio) for x in episode["sources"]):
                episode["sources"].append(stream)
        episode["provider_refs"].extend(x for x in refs if x not in episode["provider_refs"])
        current["raw"]["reference_lines"].append(line)
    for record in records:
        record["seasons"].sort(key=lambda x: x["season"])
        for season in record["seasons"]:
            season["episodes"].sort(key=lambda x: (x["episode"], x["audio"]))
    return records, quarantine


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_path(root: Path, relative: str) -> Path:
    base = root.resolve()
    target = (base / relative).resolve()
    if target != base and base not in target.parents:
        raise ValueError("catalog path escapes root: " + relative)
    return target


def parse_vod_catalog(root: Path, source_id: str = "catalog-existing") -> tuple[list, list]:
    manifest_path = root / "catalog/vod/index.json"
    manifest = _load_json(manifest_path)
    records, quarantine = [], []
    categories = manifest.get("categories", {})
    for section in ("movies", "series", "anime", "doramas"):
        info = categories.get(section)
        if not isinstance(info, dict):
            continue
        index_rel = str(info.get("index_path") or ("catalog/vod/index/" + section + ".json"))
        index_path = _safe_path(root, index_rel)
        entries = _load_json(index_path)
        if not isinstance(entries, list):
            raise ValueError("VOD index is not a list: " + index_rel)
        detail_cache = {}
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                quarantine.append({"domain": "vod", "reason": "invalid_index_entry", "raw": entry})
                continue
            detail_rel = str(entry.get("detail_path") or "")
            if not detail_rel:
                quarantine.append({"domain": "vod", "reason": "missing_detail_path", "record_id": entry.get("id"), "raw": entry})
                continue
            detail_path = _safe_path(root, detail_rel)
            if detail_rel not in detail_cache:
                detail_records = _load_json(detail_path)
                if not isinstance(detail_records, list):
                    raise ValueError("VOD detail shard is not a list: " + detail_rel)
                detail_cache[detail_rel] = {str(x.get("id")): x for x in detail_records if isinstance(x, dict) and x.get("id")}
            detail = detail_cache[detail_rel].get(str(entry["id"]))
            if not isinstance(detail, dict):
                quarantine.append({"domain": "vod", "reason": "detail_record_missing", "record_id": entry["id"], "raw": entry})
                continue
            raw = {"index": entry, "detail": detail}
            prov = input_provenance(source_id, "existing-vod-index-and-detail-json",
                                    json.dumps(raw, ensure_ascii=False, sort_keys=True),
                                    index_rel + " + " + detail_rel)
            kind = str(detail.get("subtype") or "")
            if kind not in {"movie", "series", "anime", "dorama"}:
                kind = {"movies": "movie", "series": "series", "anime": "anime", "doramas": "dorama"}.get(section, "series")
            tmdb_id = str(detail.get("tmdb_id") or entry.get("tmdb_id") or "").strip()
            imdb_id = str(detail.get("imdb_id") or entry.get("imdb_id") or "").strip()
            raw_sources = detail.get("sources") if isinstance(detail.get("sources"), list) else []
            streams = []
            for source in raw_sources:
                if isinstance(source, dict):
                    variant = _stream_variant(source, str(entry["id"]), source_id, prov, quarantine, "vod")
                    if variant:
                        streams.append(variant)
            streams = _unique_variants(streams)
            seasons = detail.get("seasons", []) if isinstance(detail.get("seasons"), list) else []
            normalized_seasons = []
            for season in seasons:
                if not isinstance(season, dict) or not str(season.get("season", "")).isdigit():
                    quarantine.append({"domain": "vod", "reason": "invalid_season_number", "record_id": entry["id"], "raw": season})
                    continue
                eps = []
                for episode in season.get("episodes", []) if isinstance(season.get("episodes"), list) else []:
                    if not isinstance(episode, dict) or not str(episode.get("episode", "")).isdigit():
                        quarantine.append({"domain": "vod", "reason": "invalid_episode_number", "record_id": entry["id"], "raw": episode})
                        continue
                    ep_sources = []
                    for source in episode.get("sources", []) if isinstance(episode.get("sources"), list) else []:
                        if isinstance(source, dict):
                            variant = _stream_variant(source, str(entry["id"]), source_id, prov, quarantine, "vod")
                            if variant:
                                ep_sources.append(variant)
                    ep_sources = _unique_variants(ep_sources)
                    eps.append({"episode": int(episode.get("episode")), "audio": episode.get("audio"),
                                "sources": ep_sources, "provider_refs": episode.get("provider_refs", []) if isinstance(episode.get("provider_refs"), list) else [],
                                "raw": episode})
                normalized_seasons.append({"season": int(season.get("season")), "episodes": eps, "raw": season})
            records.append({
                "id": str(entry["id"]), "type": kind, "title": str(detail.get("title") or entry.get("title") or ""),
                "year": str(detail.get("year") or entry.get("year")) if (detail.get("year") or entry.get("year")) is not None else None,
                "aliases": detail.get("aliases", []) if isinstance(detail.get("aliases"), list) else [], "external_ids": {"tmdb": tmdb_id or None, "imdb": imdb_id or None},
                "overview": str(detail.get("overview")) if detail.get("overview") is not None else None, "genres": detail.get("genres", []) if isinstance(detail.get("genres"), list) else [],
                "poster_url": detail.get("poster_url"), "sources": streams,
                "provider_refs": detail.get("provider_refs", []) if isinstance(detail.get("provider_refs"), list) else [], "seasons": normalized_seasons,
                "provenance": [prov], "raw": raw,
            })
    return records, quarantine


def parse_epg_sources(document: dict, source_id: str = "catalog-existing") -> tuple[list, list]:
    raw = json.dumps(document, ensure_ascii=False, sort_keys=True)
    prov = input_provenance(source_id, "epg-sources-json", raw, "catalog/epg/sources.json")
    records, quarantine = [], []
    for item in document.get("sources", []) if isinstance(document, dict) else []:
        if not isinstance(item, dict) or not item.get("id"):
            quarantine.append({"domain": "epg", "reason": "missing_source_id", "raw": item})
            continue
        records.append({"id": str(item["id"]), "domain": "epg", "name": item.get("name"), "type": item.get("type"),
                        "format": item.get("format"), "url": item.get("url") if item.get("url") and safe_stream_url(item.get("url"))[0] else None,
                        "url_template": item.get("url_template"), "priority": item.get("priority", 100),
                        "enabled": bool(item.get("enabled", False)), "match_strategy": item.get("match_strategy"),
                        "provenance": [prov], "raw": item})
    return records, quarantine


def parse_epg_mapping(document: dict, source_id: str = "catalog-existing") -> tuple[list, list]:
    raw = json.dumps(document, ensure_ascii=False, sort_keys=True)
    prov = input_provenance(source_id, "epg-channel-map-json", raw, "catalog/epg/channel-map.json")
    records = []
    for group in ("meuguia_codes", "guiadetv_slugs", "xmltv_aliases"):
        mapping = document.get(group, {}) if isinstance(document, dict) else {}
        if not isinstance(mapping, dict):
            continue
        for channel_name, value in mapping.items():
            records.append({"id": stable_id("epgmap", source_id, group + ":" + normalize_name(channel_name)),
                            "channel_name": channel_name, "mapping_type": group, "value": value,
                            "provenance": [prov], "raw": {"group": group, "key": channel_name, "value": value}})
    return records, []


def parse_xmltv(payload: bytes | str, source_id: str, source_ref: str = "input.xml",
                default_timezone=timezone.utc) -> tuple[list, list, list]:
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    prov = input_provenance(source_id, "xmltv", raw, source_ref)
    channels, programmes, quarantine = [], [], []
    try:
        iterator = ET.iterparse(io.BytesIO(raw), events=("end",))
        for _, elem in iterator:
            tag = elem.tag.rsplit("}", 1)[-1]
            if tag == "channel":
                ident = str(elem.attrib.get("id") or "").strip()
                names = [" ".join(child.text.split()) for child in elem
                         if child.tag.rsplit("}", 1)[-1] == "display-name" and child.text and child.text.strip()]
                if ident:
                    channels.append({"id": ident, "display_names": list(dict.fromkeys(names)),
                                     "source_id": source_id, "provenance": [prov], "raw": dict(elem.attrib)})
            elif tag == "programme":
                start_raw, stop_raw = elem.attrib.get("start", ""), elem.attrib.get("stop", "")
                start, stop = parse_xmltv_datetime(start_raw, default_timezone), parse_xmltv_datetime(stop_raw, default_timezone)
                title = next((" ".join(x.text.split()) for x in elem
                              if x.tag.rsplit("}", 1)[-1] == "title" and x.text and x.text.strip()), "")
                desc = next((" ".join(x.text.split()) for x in elem
                             if x.tag.rsplit("}", 1)[-1] == "desc" and x.text and x.text.strip()), None)
                if not start or not stop or stop <= start or not elem.attrib.get("channel") or not title:
                    quarantine.append({"domain": "epg", "reason": "invalid_programme", "raw": {
                        "attributes": dict(elem.attrib), "title": title, "start": start_raw, "stop": stop_raw}})
                else:
                    key = str(elem.attrib["channel"]) + "|" + start.isoformat() + "|" + title
                    programmes.append({"id": stable_id("epgprogram", source_id, key),
                                       "epg_channel_id": str(elem.attrib["channel"]),
                                       "title": title, "description": desc,
                                       "start": start.isoformat(), "stop": stop.isoformat(),
                                       "source_id": source_id, "provenance": [prov],
                                       "raw": {"attributes": dict(elem.attrib), "start": start_raw, "stop": stop_raw}})
            elem.clear()
    except ET.ParseError as exc:
        raise ValueError("invalid XMLTV document: " + str(exc)) from exc
    if not channels:
        quarantine.append({"domain": "epg", "reason": "no_xmltv_channels"})
    return channels, programmes, quarantine


def parse_xmltv_datetime(value: str, default_timezone=timezone.utc):
    match = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:\s*([+-])(\d{2})(\d{2}))?", value or "")
    if not match:
        return None
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    sign, oh, om = match.groups()[6:]
    offset = timedelta(hours=int(oh or 0), minutes=int(om or 0))
    if sign == "-":
        offset = -offset
    tz = timezone(offset) if sign else default_timezone
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=tz)
    except ValueError:
        return None


def parse_logo_references(channels: list, radios: list, source_id: str = "catalog-existing") -> tuple[list, list]:
    assets, quarantine, seen = [], [], set()
    for domain, records in (("channel", channels), ("radio", radios)):
        for record in records:
            url = str(record.get("logo_url") or "").strip()
            if not url:
                continue
            ok, reason = safe_stream_url(url)
            if not ok:
                quarantine.append({"domain": "logos", "reason": reason, "entity_id": record.get("id"), "raw": url})
                continue
            key = (domain, str(record.get("id")), url)
            if key in seen:
                continue
            seen.add(key)
            prov = record.get("provenance", [])
            assets.append({"id": stable_id("asset", source_id, "|".join(key)),
                           "entity_id": record.get("id"), "kind": domain + "_logo",
                           "url": url, "mime_type": None, "width": None, "height": None,
                           "source_id": source_id, "status": "unverified",
                           "is_primary": True, "provenance": prov,
                           "raw": {"logo_url": url, "domain": domain}})
    return assets, quarantine

def parse_source_registry(document: dict, source_id: str = "source-registry") -> tuple[list, list]:
    raw = json.dumps(document, ensure_ascii=False, sort_keys=True)
    prov = input_provenance(source_id, "source-registry-json", raw, "sources/sources.json")
    records, quarantine = [], []
    domain_map = {"channel": "channels", "channels": "channels", "radio": "radios",
                  "radios": "radios", "vod": "vod", "epg": "epg", "logos": "logos"}
    for item in document.get("sources", []) if isinstance(document, dict) else []:
        if not isinstance(item, dict) or not item.get("id"):
            quarantine.append({"domain": "sources", "reason": "missing_source_id", "raw": item})
            continue
        domain = domain_map.get(str(item.get("category") or "").casefold())
        if not domain:
            quarantine.append({"domain": "sources", "reason": "unsupported_source_domain", "raw": item})
            continue
        try:
            priority = int(item.get("priority", 100))
        except (TypeError, ValueError):
            priority = 100
        url = item.get("url")
        if url and not safe_stream_url(url)[0]:
            quarantine.append({"domain": "sources", "reason": "invalid_source_url", "raw": item})
            url = None
        records.append({"id": str(item["id"]), "domain": domain,
                        "name": item.get("name"), "format": str(item.get("format") or "unknown"),
                        "url": url or None, "url_template": item.get("url_template"),
                        "priority": priority, "enabled": bool(item.get("enabled", False)),
                        "license": item.get("license"), "match_strategy": item.get("match_strategy"),
                        "provenance": [prov], "raw": item})
    return records, quarantine


def parse_xmltv(payload: bytes | str, source_id: str, source_ref: str = "input.xml",
                default_timezone=timezone.utc):
    from acervo_v2.xmltv import parse_xmltv as parse
    return parse(payload, source_id, source_ref, default_timezone)
