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


def _variant_internal_id(entity_id: str, source_id: str, url: str, audio: object = None,
                          scope: str = "entity", source_type: object = None) -> str:
    identity = json.dumps([entity_id, scope, url, str(audio or ""), str(source_type or "")],
                          ensure_ascii=False, separators=(",", ":"))
    return stable_id("stream", source_id, identity)


def _stream_variant(item: dict, entity_id: str, source_id: str, provenance: dict,
                    quarantine: list, domain: str = "stream",
                    scope: str = "entity") -> dict | None:
    url = str(item.get("url") or item.get("stream_url") or "").strip()
    ok, reason = safe_stream_url(url)
    if not ok:
        quarantine.append({"domain": domain, "reason": reason, "entity_id": entity_id,
                           "source_id": source_id, "provenance": [provenance], "raw": item})
        return None
    if domain == "radio" and is_image_url(url):
        quarantine.append({"domain": domain, "reason": "image_url_in_audio_stream", "entity_id": entity_id,
                           "source_id": source_id, "provenance": [provenance], "raw": item})
        return None
    variant_source = str(item.get("source_id") or source_id)
    try:
        priority = int(item.get("priority", 100) or 100)
    except (TypeError, ValueError):
        priority = 100
    status = str(item.get("status") or "unverified")
    if status not in {"unverified", "imported", "validated", "reachable", "unavailable", "quarantined", "unknown"}:
        status = "unknown"
    audio, source_type = item.get("audio"), item.get("source_type")
    result = {
        "id": _variant_internal_id(entity_id, variant_source, url, audio, scope, source_type),
        "entity_id": entity_id, "source_id": variant_source, "url": url,
        "protocol": urlsplit(url).scheme.lower(), "priority": priority,
        "audio": audio, "scope": scope, "status": status,
        "provenance": [provenance], "raw": item,
    }
    if source_type is not None:
        result["source_type"] = source_type
    if item.get("id") is not None:
        result["provider_variant_id"] = str(item["id"])
    return result


def _record_id(domain: str, item: dict, source_id: str, key: str) -> str:
    return str(item.get("id") or stable_id(domain, source_id, str(item.get(key) or key)))


def _unique_variants(streams: list[dict]) -> list[dict]:
    """Collapse exact same owner/scope/source/URL/audio variants without losing provenance."""
    result, by_key = [], {}
    for stream in streams:
        key = (stream.get("entity_id"), stream.get("scope", "entity"),
               stream.get("source_id"), stream.get("url"), stream.get("audio"),
               stream.get("source_type"))
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = stream
            result.append(stream)
            continue
        for provenance in stream.get("provenance", []):
            if provenance not in existing.setdefault("provenance", []):
                existing["provenance"].append(provenance)
        existing["priority"] = min(int(existing.get("priority", 100)),
                                   int(stream.get("priority", 100)))
        provider_ids = set(existing.get("provider_variant_ids", []))
        if existing.get("provider_variant_id"):
            provider_ids.add(existing["provider_variant_id"])
        if stream.get("provider_variant_id"):
            provider_ids.add(stream["provider_variant_id"])
        if provider_ids:
            existing["provider_variant_ids"] = sorted(provider_ids)
        raw_variants = list(existing.get("raw_variants", []))
        if stream.get("raw") != existing.get("raw") and stream.get("raw") not in raw_variants:
            raw_variants.append(stream.get("raw"))
        if raw_variants:
            existing["raw_variants"] = raw_variants
    return result


def _merge_values(primary: list, incoming: list) -> list:
    result = list(primary or [])
    for value in incoming or []:
        if value not in result:
            result.append(value)
    return result


def _merge_vod_seasons(primary: list, incoming: list) -> list:
    seasons = {int(item["season"]): item for item in (primary or [])}
    for source_season in incoming or []:
        number = int(source_season["season"])
        target = seasons.get(number)
        if target is None:
            seasons[number] = source_season
            continue
        if source_season.get("raw") != target.get("raw") and source_season.get("raw") is not None:
            target["raw_alternates"] = _merge_values(target.get("raw_alternates", []), [source_season["raw"]])
        episodes = {(int(item["episode"]), item.get("audio")): item for item in target.get("episodes", [])}
        for source_episode in source_season.get("episodes", []):
            key = (int(source_episode["episode"]), source_episode.get("audio"))
            episode = episodes.get(key)
            if episode is None:
                target.setdefault("episodes", []).append(source_episode)
                episodes[key] = source_episode
                continue
            episode["sources"] = _unique_variants(
                list(episode.get("sources", [])) + list(source_episode.get("sources", [])))
            episode["provider_refs"] = _merge_values(
                episode.get("provider_refs", []), source_episode.get("provider_refs", []))
            if source_episode.get("raw") != episode.get("raw") and source_episode.get("raw") is not None:
                episode["raw_alternates"] = _merge_values(
                    episode.get("raw_alternates", []), [source_episode["raw"]])
    result = sorted(seasons.values(), key=lambda item: int(item["season"]))
    for season in result:
        season["episodes"] = sorted(
            season.get("episodes", []),
            key=lambda item: (int(item["episode"]), str(item.get("audio") or "")))
    return result


def _merge_vod_records(primary: dict, incoming: dict) -> dict:
    """Merge records already resolved to the same provider-backed VOD identity."""
    if primary["id"] != incoming["id"]:
        raise ValueError("cannot merge VOD records with different canonical IDs")
    if incoming.get("title") and incoming["title"] != primary.get("title"):
        primary["aliases"] = _merge_values(primary.get("aliases", []), [incoming["title"]])
    primary["aliases"] = _merge_values(primary.get("aliases", []), incoming.get("aliases", []))
    primary["genres"] = _merge_values(primary.get("genres", []), incoming.get("genres", []))
    primary["sources"] = _unique_variants(list(primary.get("sources", [])) + list(incoming.get("sources", [])))
    primary["provider_refs"] = _merge_values(primary.get("provider_refs", []), incoming.get("provider_refs", []))
    primary["seasons"] = _merge_vod_seasons(primary.get("seasons", []), incoming.get("seasons", []))
    primary["provenance"] = _merge_values(primary.get("provenance", []), incoming.get("provenance", []))
    primary["legacy_ids"] = _merge_values(primary.get("legacy_ids", []), incoming.get("legacy_ids", []))
    primary["catalog_sections"] = _merge_values(primary.get("catalog_sections", []), incoming.get("catalog_sections", []))
    primary_identity = primary.setdefault("identity_resolution", {})
    incoming_identity = incoming.get("identity_resolution", {})
    primary_identity["legacy_id_conflict"] = bool(
        primary_identity.get("legacy_id_conflict") or incoming_identity.get("legacy_id_conflict")
    )
    identity_overrides = []
    for identity in (primary_identity, incoming_identity):
        values = list(identity.get("identity_overrides", []))
        if identity.get("identity_override"):
            values.append(identity["identity_override"])
        for value in values:
            if value not in identity_overrides:
                identity_overrides.append(value)
    if identity_overrides:
        primary_identity["identity_overrides"] = identity_overrides
        primary_identity["identity_override"] = identity_overrides[0]
    primary_external = primary.setdefault("external_ids", {})
    incoming_external = incoming.get("external_ids", {})
    for provider in ("tmdb", "imdb"):
        value, current = incoming_external.get(provider), primary_external.get(provider)
        if value and not current:
            primary_external[provider] = value
        elif value and current and str(value) != str(current):
            alternates = primary_external.setdefault("alternates", [])
            candidate = {"provider": provider, "id": str(value)}
            if candidate not in alternates:
                alternates.append(candidate)
    for field in ("year", "overview", "poster_url"):
        value, current = incoming.get(field), primary.get(field)
        if value not in (None, "") and current in (None, ""):
            primary[field] = value
        elif value not in (None, "") and current not in (None, "") and value != current:
            conflicts = primary.setdefault("raw", {}).setdefault("metadata_conflicts", [])
            conflict = {"field": field, "primary": current, "alternate": value,
                        "alternate_source_refs": [p.get("source_ref") for p in incoming.get("provenance", [])]}
            if conflict not in conflicts:
                conflicts.append(conflict)
    primary_raw, incoming_raw = primary.setdefault("raw", {}), incoming.get("raw", {})
    if incoming_raw.get("index") is not None:
        alternate_index = {"catalog_section": incoming_raw.get("catalog_section"), "index": incoming_raw["index"]}
        if incoming_raw.get("identity_override"):
            alternate_index["identity_override"] = incoming_raw["identity_override"]
        primary_raw["alternate_indexes"] = _merge_values(primary_raw.get("alternate_indexes", []), [alternate_index])
    if incoming_raw.get("detail") is not None and incoming_raw.get("detail") != primary_raw.get("detail"):
        alternate_detail = {"catalog_section": incoming_raw.get("catalog_section"), "detail": incoming_raw["detail"]}
        if incoming_raw.get("identity_override"):
            alternate_detail["identity_override"] = incoming_raw["identity_override"]
        primary_raw["alternate_details"] = _merge_values(primary_raw.get("alternate_details", []), [alternate_detail])
    return primary


def _rekey_vod_variants(record: dict, entity_id: str) -> None:
    record["id"] = entity_id
    for variant in record.get("sources", []):
        variant["entity_id"] = entity_id
        variant["id"] = _variant_internal_id(entity_id, variant["source_id"], variant["url"],
            variant.get("audio"), variant.get("scope", "entity"), variant.get("source_type"))
    for season in record.get("seasons", []):
        for episode in season.get("episodes", []):
            for variant in episode.get("sources", []):
                variant["entity_id"] = entity_id
                variant["id"] = _variant_internal_id(entity_id, variant["source_id"], variant["url"],
                    variant.get("audio"), variant.get("scope", "entity"), variant.get("source_type"))


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
        if not raw_streams:
            quarantine.append({
                "domain": "radios", "reason": "missing_stream_url", "entity_id": ident,
                "source_id": source_id, "provenance": [prov], "raw": item,
            })
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



def apply_radio_reference_recovery(records: list, quarantine: list, document: dict,
                                   source_ref: str = "sources/reference/radio-recovery.json") -> dict:
    """Recover misaligned radio name/stream fields from an exact, pinned reference snapshot."""
    if not isinstance(document, dict) or not isinstance(document.get("records"), list):
        return {"reference_records": 0, "applied_records": 0, "streams_added": 0,
                "logo_candidates_promoted": 0, "quarantine_items_resolved": 0,
                "unmatched_reference_records": 0, "records_without_reference_match": len(records)}
    source = document.get("source") if isinstance(document.get("source"), dict) else {}
    source_id = str(source.get("source_id") or "reference-radio-catalog")
    source_external_ref = str(source.get("source_ref") or "")
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True)
    provenance = input_provenance(source_id, "radio-reference-recovery-json", payload, source_ref)

    def normalized_url(value):
        return str(value or "").strip().rstrip("/").casefold()

    by_id, seen_urls = {}, set()
    for item in document.get("records", []):
        if not isinstance(item, dict) or not item.get("record_id"):
            raise ValueError("radio reference recovery entry is missing record_id")
        record_id = str(item["record_id"])
        source_url = normalized_url(item.get("source_name_url"))
        if record_id in by_id or not source_url or source_url in seen_urls:
            raise ValueError("radio reference recovery contains duplicate IDs or source URLs")
        if int(item.get("match_count", 0)) != 1:
            raise ValueError("radio reference recovery contains a non-unique match")
        by_id[record_id] = item
        seen_urls.add(source_url)
    expected_reference_records = source.get("expected_records")
    if expected_reference_records is not None and len(by_id) != int(expected_reference_records):
        raise ValueError(
            "radio reference record count changed: expected "
            + str(expected_reference_records) + ", got " + str(len(by_id))
        )

    applied_ids, invalid_match_ids = set(), []
    streams_added = logo_candidates_promoted = quarantine_items_resolved = 0
    for record in records:
        record_id = str(record.get("id") or "")
        reference = by_id.get(record_id)
        if reference is None:
            continue
        raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
        original_name_url = str(raw.get("name") or "").strip()
        if normalized_url(original_name_url) != normalized_url(reference.get("source_name_url")):
            invalid_match_ids.append(record_id)
            quarantine.append({
                "domain": "radios", "reason": "radio_reference_source_mismatch",
                "entity_id": record_id, "source_id": source_id,
                "provenance": [provenance], "raw": reference,
            })
            continue
        recovered_name = str(reference.get("name") or "").strip()
        recovered_url = str(reference.get("stream_url") or "").strip()
        if not recovered_name:
            invalid_match_ids.append(record_id)
            quarantine.append({
                "domain": "radios", "reason": "radio_reference_missing_name",
                "entity_id": record_id, "source_id": source_id,
                "provenance": [provenance], "raw": reference,
            })
            continue
        if normalized_url(recovered_url) != normalized_url(original_name_url):
            invalid_match_ids.append(record_id)
            quarantine.append({
                "domain": "radios", "reason": "radio_reference_stream_mismatch",
                "entity_id": record_id, "source_id": source_id,
                "provenance": [provenance], "raw": reference,
            })
            continue
        valid, reason = safe_stream_url(recovered_url)
        if not valid:
            invalid_match_ids.append(record_id)
            quarantine.append({
                "domain": "radios", "reason": "radio_reference_invalid_stream_url",
                "entity_id": record_id, "source_id": source_id,
                "provenance": [provenance], "raw": reference, "validation_reason": reason,
            })
            continue
        variant_source_id = str(record.get("source_id") or "catalog-existing")
        variant = _stream_variant(
            {"url": recovered_url}, record_id, variant_source_id,
            provenance, quarantine, domain="radio",
        )
        existing_urls = {str(item.get("url") or "") for item in record.get("streams", [])}
        stream_added = bool(variant and variant.get("url") not in existing_urls)
        if stream_added:
            record.setdefault("streams", []).append(variant)
            streams_added += 1
        record["name"] = recovered_name
        logo_candidate = str(reference.get("logo_url_candidate") or "").strip()
        logo_status = None
        if logo_candidate and is_image_url(logo_candidate) and safe_stream_url(logo_candidate)[0]:
            if not record.get("logo_url"):
                record["logo_url"] = logo_candidate
                logo_candidates_promoted += 1
            logo_status = "unverified"
        record.setdefault("provenance", [])
        if provenance not in record["provenance"]:
            record["provenance"].append(provenance)
        record["reference_recovery"] = {
            "source_id": source_id, "source_ref": source_external_ref,
            "source_commit": source.get("commit"), "source_blob_sha": source.get("blob_sha"),
            "reference_line": reference.get("reference_line"),
            "match_method": reference.get("match_method"), "match_count": reference.get("match_count"),
            "original_name_url": original_name_url,
            "original_stream_url": reference.get("original_stream_url"),
            "recovered_name": recovered_name, "recovered_stream_url": recovered_url,
            "stream_added": stream_added, "logo_url_candidate": logo_candidate or None,
            "logo_status": logo_status,
        }
        applied_ids.add(record_id)
        for rejected in quarantine:
            if (rejected.get("domain") in {"radio", "radios"}
                    and str(rejected.get("entity_id") or "") == record_id
                    and not rejected.get("resolution")):
                rejected["resolution"] = {
                    "status": "recovered_from_pinned_reference", "reference_id": record_id,
                    "source_ref": source_external_ref, "source_commit": source.get("commit"),
                    "recovered_stream_url": recovered_url,
                }
                quarantine_items_resolved += 1
    expected_applied_records = source.get("expected_applied_records")
    if expected_applied_records is not None and len(applied_ids) != int(expected_applied_records):
        raise ValueError(
            "radio reference applied count changed: expected "
            + str(expected_applied_records) + ", got " + str(len(applied_ids))
        )
    return {
        "reference_records": len(by_id), "applied_records": len(applied_ids),
        "streams_added": streams_added, "logo_candidates_promoted": logo_candidates_promoted,
        "quarantine_items_resolved": quarantine_items_resolved,
        "unmatched_reference_records": len(set(by_id) - applied_ids),
        "records_without_reference_match": sum(str(item.get("id") or "") not in by_id for item in records),
        "invalid_match_ids": sorted(invalid_match_ids), "source_id": source_id,
        "source_ref": source_external_ref, "source_commit": source.get("commit"),
    }


def _reference_sources(value: str, entity_id: str, source_id: str, prov: dict,
                       quarantine: list, domain: str, audio: str | None = None,
                       scope: str = "entity") -> tuple[list, list]:
    streams, refs = [], []
    for token in (value or "").split(","):
        token = token.strip()
        if not token:
            continue
        if token.lower().startswith(("http://", "https://")):
            variant = _stream_variant({"url": token, "source_id": source_id, "audio": audio},
                                      entity_id, source_id, prov, quarantine, domain=domain, scope=scope)
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
            streams, refs = _reference_sources(value, record["id"], source_id, prov, quarantine, "vod", audio=audio)
            for stream in streams:
                stream["audio"] = audio
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
        streams, refs = _reference_sources(fields[3], current["id"], source_id, prov, quarantine, "vod", audio=audio,
                                               scope=f"season:{season_no}:episode:{episode_no}:audio:{audio or 'unknown'}")
        for stream in streams:
            stream["audio"] = audio
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


def _vod_identity_key(entry: dict, section: str) -> str:
    kind = str(entry.get("subtype") or "").strip().lower()
    if kind not in {"movie", "series", "anime", "dorama"}:
        kind = {"movies": "movie", "series": "series", "anime": "anime", "doramas": "dorama"}.get(section, "series")
    external = entry.get("external_ids") if isinstance(entry.get("external_ids"), dict) else {}
    tmdb = str(entry.get("tmdb_id") or external.get("tmdb") or "").strip()
    imdb = str(entry.get("imdb_id") or external.get("imdb") or "").strip()
    year = str(entry.get("year") or "").strip()
    language = normalize_name(entry.get("language") or entry.get("original_language"))
    # External IDs corroborate identity only when media type and year agree.
    # If year is absent, matching stays scoped to the existing internal ID.
    if tmdb and year:
        return f"{kind}|tmdb:{tmdb}|year:{year}|language:{language or '*'}"
    if imdb and year:
        return f"{kind}|imdb:{imdb}|year:{year}|language:{language or '*'}"
    if tmdb:
        return f"{kind}|legacy:{entry.get('id')}|tmdb:{tmdb}|year:*|language:{language or '*'}"
    if imdb:
        return f"{kind}|legacy:{entry.get('id')}|imdb:{imdb}|year:*|language:{language or '*'}"
    return f"{kind}|legacy:{entry.get('id')}|title:{normalize_name(entry.get('title'))}|year:{year}|language:{language or '*'}"


def _allocate_vod_identity_ids(identity_groups: dict, all_legacy_ids: set) -> dict:
    keys_by_legacy_id = {}
    for identity_key, references in identity_groups.items():
        for _, _, _, entry in references:
            keys_by_legacy_id.setdefault(str(entry["id"]), set()).add(identity_key)
    allocated, result = set(), {}
    for identity_key in sorted(identity_groups):
        legacy_ids = sorted({str(ref[3]["id"]) for ref in identity_groups[identity_key]})
        preferred = sorted(legacy_ids, key=lambda ident: (len(keys_by_legacy_id[ident]) > 1, ident))
        canonical = None
        for ident in preferred:
            owners = keys_by_legacy_id[ident]
            if ident not in allocated and (len(owners) == 1 or identity_key == min(owners)):
                canonical = ident
                break
        if canonical is None:
            base = legacy_ids[0]
            digest, size = hashlib.sha256(identity_key.encode("utf-8")).hexdigest(), 12
            canonical = f"{base}~{digest[:size]}"
            while canonical in allocated or canonical in all_legacy_ids:
                size += 4
                canonical = f"{base}~{digest[:size]}"
        if canonical in allocated:
            raise ValueError("deterministic VOD identity allocation collision: " + canonical)
        allocated.add(canonical)
        result[identity_key] = canonical
    return result


def iter_vod_catalog(root: Path, source_id: str = "catalog-existing",
                    quarantine: list | None = None,
                    identity_report: dict | None = None,
                    identity_overrides: dict | None = None):
    """Yield canonical VOD entities, merging repeated index references by provider identity."""
    quarantine = quarantine if quarantine is not None else []
    identity_report = identity_report if identity_report is not None else {}
    override_document = identity_overrides if isinstance(identity_overrides, dict) else {}
    override_source = override_document.get("source") if isinstance(override_document.get("source"), dict) else {}
    override_rules = override_document.get("overrides", []) if isinstance(override_document.get("overrides"), list) else []
    override_input_path = "sources/reference/vod-identity-overrides.json"
    override_payload = json.dumps(override_document, ensure_ascii=False, sort_keys=True)
    override_provenance = input_provenance(
        str(override_source.get("source_id") or "reference-vod-identity"),
        "explicit-vod-identity-overrides-json", override_payload, override_input_path,
    ) if override_rules else None
    applied_override_refs = {}
    manifest = _load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {})
    section_entries, identity_groups, all_legacy_ids = [], {}, set()

    def find_identity_override(entry, section):
        external = entry.get("external_ids") if isinstance(entry.get("external_ids"), dict) else {}
        source_tmdb = str(entry.get("tmdb_id") or external.get("tmdb") or "").strip()
        title_key = normalize_name(entry.get("title"))
        year = str(entry.get("year") or "").strip()
        media_type = str(entry.get("subtype") or "").strip().lower()
        legacy_id = str(entry.get("id") or "")
        for rule in override_rules:
            match = rule.get("match") if isinstance(rule.get("match"), dict) else {}
            titles = match.get("titles") if isinstance(match.get("titles"), list) else ([match["title"]] if match.get("title") else [])
            allowed_sections = match.get("catalog_sections") if isinstance(match.get("catalog_sections"), list) else []
            allowed_legacy_ids = match.get("legacy_ids") if isinstance(match.get("legacy_ids"), list) else []
            if (title_key not in {normalize_name(value) for value in titles}
                    or year != str(match.get("year") or "").strip()
                    or source_tmdb != str(match.get("tmdb_id") or "").strip()
                    or media_type != str(match.get("media_type") or "").strip().lower()
                    or section not in allowed_sections
                    or (allowed_legacy_ids and legacy_id not in allowed_legacy_ids)):
                continue
            canonical = rule.get("canonical") if isinstance(rule.get("canonical"), dict) else {}
            canonical_tmdb = str(canonical.get("tmdb_id") or "").strip()
            if not canonical_tmdb:
                raise ValueError("VOD identity override has no canonical TMDB ID: " + str(rule.get("id")))
            source_files = override_source.get("files") if isinstance(override_source.get("files"), list) else []
            external_ref = next((item.get("source_ref") for item in source_files if item.get("source_ref")), None)
            return {
                "id": str(rule.get("id") or ""), "source_tmdb_id": source_tmdb,
                "canonical_tmdb_id": canonical_tmdb,
                "canonical_title": str(canonical.get("title") or ""),
                "source_ref": external_ref, "source_commit": override_source.get("commit"),
                "reason": rule.get("reason"), "evidence": rule.get("evidence", []),
            }
        return None
    for section in ("movies", "series", "anime", "doramas"):
        info = categories.get(section)
        if not isinstance(info, dict):
            continue
        index_rel = str(info.get("index_path") or ("catalog/vod/index/" + section + ".json"))
        entries = _load_json(_safe_path(root, index_rel))
        if not isinstance(entries, list):
            raise ValueError("VOD index is not a list: " + index_rel)
        entries_by_detail = {}
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("id"):
                quarantine.append({"domain": "vod", "reason": "invalid_index_entry", "raw": entry})
                continue
            detail_rel = str(entry.get("detail_path") or "")
            if not detail_rel:
                quarantine.append({"domain": "vod", "reason": "missing_detail_path",
                                   "record_id": entry.get("id"), "raw": entry})
                continue
            _safe_path(root, detail_rel)
            identity_entry = dict(entry)
            override_info = find_identity_override(entry, section)
            if override_info:
                identity_entry["_source_entry"] = entry
                identity_entry["_identity_override"] = override_info
                identity_entry["tmdb_id"] = override_info["canonical_tmdb_id"]
                external_ids = dict(entry.get("external_ids") or {})
                external_ids["tmdb"] = override_info["canonical_tmdb_id"]
                identity_entry["external_ids"] = external_ids
                applied_override_refs.setdefault(override_info["id"], []).append({
                    "catalog_section": section, "index_path": index_rel, "detail_path": detail_rel,
                    "legacy_id": str(entry["id"]), "source_tmdb_id": override_info["source_tmdb_id"],
                    "canonical_tmdb_id": override_info["canonical_tmdb_id"],
                })
            entries_by_detail.setdefault(detail_rel, []).append(identity_entry)
            all_legacy_ids.add(str(identity_entry["id"]))
            identity_key = _vod_identity_key(identity_entry, section)
            identity_groups.setdefault(identity_key, []).append((section, index_rel, detail_rel, identity_entry))
        section_entries.append((section, index_rel, entries_by_detail))

    for rule in override_rules:
        expected_matches = rule.get("expected_matches")
        actual_matches = len(applied_override_refs.get(str(rule.get("id") or ""), []))
        if expected_matches is not None and actual_matches != int(expected_matches):
            raise ValueError(
                "VOD identity override match count changed for "
                + str(rule.get("id")) + ": expected " + str(expected_matches)
                + ", got " + str(actual_matches)
            )
    final_ids = _allocate_vod_identity_ids(identity_groups, all_legacy_ids)
    keys_by_legacy_id = {}
    for identity_key, references in identity_groups.items():
        for _, _, _, entry in references:
            keys_by_legacy_id.setdefault(str(entry["id"]), set()).add(identity_key)
    aggregate_keys = {
        key for key, references in identity_groups.items()
        if len(references) > 1 or any(len(keys_by_legacy_id[str(ref[3]["id"])]) > 1 for ref in references)
    }
    reused_legacy_ids = {ident for ident, keys in keys_by_legacy_id.items() if len(keys) > 1}
    merged_groups = [references for references in identity_groups.values() if len(references) > 1]
    identity_report = identity_report if identity_report is not None else {}
    identity_report.update({
        "input_index_entries": sum(len(references) for references in identity_groups.values()),
        "canonical_identity_groups": len(identity_groups),
        "identity_groups_merged": len(merged_groups),
        "index_entries_consolidated": sum(len(references) - 1 for references in merged_groups),
        "same_legacy_id_duplicate_groups": sum(
            1 for references in merged_groups
            if any(count > 1 for count in __import__("collections").Counter(
                str(ref[3]["id"]) for ref in references
            ).values())
        ),
        "provider_identity_groups_merged_across_legacy_ids": sum(
            1 for references in merged_groups
            if len({str(ref[3]["id"]) for ref in references}) > 1
        ),
        "legacy_ids_reused_across_distinct_identities": len(reused_legacy_ids),
        "identity_groups_affected_by_legacy_id_conflict": sum(
            1 for references in identity_groups.values()
            if any(str(ref[3]["id"]) in reused_legacy_ids for ref in references)
        ),
    })

    def audit_identity_group(identity_key: str, references: list) -> dict:
        index_references = []
        for section, index_rel, detail_rel, entry in references:
            external = entry.get("external_ids") if isinstance(entry.get("external_ids"), dict) else {}
            media_type = str(entry.get("subtype") or "").strip().lower()
            if media_type not in {"movie", "series", "anime", "dorama"}:
                media_type = {"movies": "movie", "series": "series",
                              "anime": "anime", "doramas": "dorama"}.get(section, "series")
            tmdb_id = str(entry.get("tmdb_id") or external.get("tmdb") or "").strip()
            imdb_id = str(entry.get("imdb_id") or external.get("imdb") or "").strip()
            override_info = entry.get("_identity_override") if isinstance(entry.get("_identity_override"), dict) else {}
            index_references.append({
                "catalog_section": section, "index_path": index_rel, "detail_path": detail_rel,
                "legacy_id": str(entry.get("id") or ""), "title": str(entry.get("title") or ""),
                "media_type": media_type, "year": str(entry.get("year") or "").strip() or None,
                "tmdb_id": tmdb_id or None,
                "source_tmdb_id": str(override_info.get("source_tmdb_id") or tmdb_id or "").strip() or None,
                "identity_override_id": override_info.get("id"), "imdb_id": imdb_id or None,
            })
        index_references.sort(key=lambda item: (
            item["catalog_section"], item["index_path"], item["detail_path"],
            item["legacy_id"], item["title"],
        ))
        return {
            "canonical_id": final_ids[identity_key],
            "identity_key": identity_key,
            "identity_key_sha256": hashlib.sha256(identity_key.encode("utf-8")).hexdigest(),
            "legacy_ids": sorted({item["legacy_id"] for item in index_references if item["legacy_id"]}),
            "catalog_sections": sorted({item["catalog_section"] for item in index_references}),
            "media_types": sorted({item["media_type"] for item in index_references}),
            "years": sorted({item["year"] for item in index_references if item["year"]}),
            "tmdb_ids": sorted({item["tmdb_id"] for item in index_references if item["tmdb_id"]}),
            "source_tmdb_ids": sorted({item["source_tmdb_id"] for item in index_references if item["source_tmdb_id"]}),
            "identity_override_ids": sorted({item["identity_override_id"] for item in index_references if item["identity_override_id"]}),
            "imdb_ids": sorted({item["imdb_id"] for item in index_references if item["imdb_id"]}),
            "index_reference_count": len(index_references),
            "entries_consolidated": max(0, len(index_references) - 1),
            "index_references": index_references,
        }

    identity_report["identity_audit_version"] = 2
    identity_report["identity_override_rules"] = len(override_rules)
    identity_report["identity_override_index_references"] = sum(len(value) for value in applied_override_refs.values())
    identity_report["identity_overrides"] = [
        {
            "id": str(rule.get("id") or ""), "source": override_source,
            "match": rule.get("match", {}), "canonical": rule.get("canonical", {}),
            "evidence": rule.get("evidence", []), "candidate_evidence": rule.get("candidate_evidence", {}),
            "reason": rule.get("reason"), "expected_matches": rule.get("expected_matches"),
            "applied_index_reference_count": len(applied_override_refs.get(str(rule.get("id") or ""), [])),
            "applied_index_references": sorted(
                applied_override_refs.get(str(rule.get("id") or ""), []),
                key=lambda item: (item["catalog_section"], item["index_path"], item["detail_path"], item["legacy_id"]),
            ),
        }
        for rule in override_rules
    ]
    identity_report["consolidations"] = [
        audit_identity_group(identity_key, references)
        for identity_key, references in sorted(identity_groups.items())
        if len(references) > 1
    ]
    identity_report["legacy_id_conflicts"] = [
        {
            "legacy_id": legacy_id,
            "identity_groups": [
                audit_identity_group(identity_key, identity_groups[identity_key])
                for identity_key in sorted(keys_by_legacy_id[legacy_id])
            ],
        }
        for legacy_id in sorted(reused_legacy_ids)
    ]

    aggregated = {}
    output_records = 0

    for section, index_rel, entries_by_detail in section_entries:
        for detail_rel in sorted(entries_by_detail):
            detail_records = _load_json(_safe_path(root, detail_rel))
            if not isinstance(detail_records, list):
                raise ValueError("VOD detail shard is not a list: " + detail_rel)
            detail_by_id = {
                str(item.get("id")): item for item in detail_records
                if isinstance(item, dict) and item.get("id")
            }
            for entry in entries_by_detail[detail_rel]:
                source_entry = entry.get("_source_entry", entry)
                override_info = entry.get("_identity_override") if isinstance(entry.get("_identity_override"), dict) else None
                source_detail = detail_by_id.get(str(entry["id"]))
                if not isinstance(source_detail, dict):
                    quarantine.append({"domain": "vod", "reason": "detail_record_missing",
                                       "record_id": entry["id"], "raw": source_entry})
                    continue
                detail = source_detail
                if override_info:
                    detail = dict(source_detail)
                    detail["tmdb_id"] = override_info["canonical_tmdb_id"]
                    detail_external_ids = dict(source_detail.get("external_ids") or {})
                    detail_external_ids["tmdb"] = override_info["canonical_tmdb_id"]
                    detail["external_ids"] = detail_external_ids
                raw = {"index": source_entry, "detail": source_detail, "catalog_section": section}
                prov = input_provenance(source_id, "existing-vod-index-and-detail-json",
                    json.dumps(raw, ensure_ascii=False, sort_keys=True), index_rel + " + " + detail_rel)
                if override_info:
                    raw["identity_override"] = override_info
                record_provenance = [prov]
                if override_info and override_provenance:
                    record_provenance.append(override_provenance)
                kind = str(detail.get("subtype") or entry.get("subtype") or "").strip().lower()
                if kind not in {"movie", "series", "anime", "dorama"}:
                    kind = {"movies": "movie", "series": "series", "anime": "anime", "doramas": "dorama"}.get(section, "series")
                identity_key = _vod_identity_key(entry, section)
                canonical_id = final_ids[identity_key]
                tmdb_id = str(detail.get("tmdb_id") or entry.get("tmdb_id") or "").strip()
                imdb_id = str(detail.get("imdb_id") or entry.get("imdb_id") or "").strip()
                raw_sources = detail.get("sources") if isinstance(detail.get("sources"), list) else []
                streams = []
                for source in raw_sources:
                    if isinstance(source, dict):
                        variant = _stream_variant(source, canonical_id, source_id, prov, quarantine,
                                                  "vod", scope="entity")
                        if variant:
                            streams.append(variant)
                streams = _unique_variants(streams)
                if override_info and override_provenance:
                    for variant in streams:
                        variant["provenance"] = _merge_values(variant.get("provenance", []), [override_provenance])
                normalized_seasons = []
                for season in detail.get("seasons", []) if isinstance(detail.get("seasons"), list) else []:
                    if not isinstance(season, dict) or not str(season.get("season", "")).isdigit():
                        quarantine.append({"domain": "vod", "reason": "invalid_season_number",
                                           "record_id": entry["id"], "raw": season})
                        continue
                    season_number = int(season.get("season"))
                    episodes = []
                    for episode in season.get("episodes", []) if isinstance(season.get("episodes"), list) else []:
                        if not isinstance(episode, dict) or not str(episode.get("episode", "")).isdigit():
                            quarantine.append({"domain": "vod", "reason": "invalid_episode_number",
                                               "record_id": entry["id"], "raw": episode})
                            continue
                        episode_number, episode_audio = int(episode.get("episode")), episode.get("audio")
                        scope = f"season:{season_number}:episode:{episode_number}:audio:{episode_audio or 'unknown'}"
                        episode_sources = []
                        for source in episode.get("sources", []) if isinstance(episode.get("sources"), list) else []:
                            if isinstance(source, dict):
                                variant = _stream_variant(source, canonical_id, source_id, prov, quarantine,
                                                          "vod", scope=scope)
                                if variant:
                                    episode_sources.append(variant)
                        episodes.append({
                            "episode": episode_number, "audio": episode_audio,
                            "sources": _unique_variants(episode_sources),
                            "provider_refs": episode.get("provider_refs", [])
                                if isinstance(episode.get("provider_refs"), list) else [],
                            "raw": episode,
                        })
                    if override_info and override_provenance:
                        for episode_record in episodes:
                            for variant in episode_record.get("sources", []):
                                variant["provenance"] = _merge_values(variant.get("provenance", []), [override_provenance])
                    normalized_seasons.append({"season": season_number, "episodes": episodes, "raw": season})
                record = {
                    "id": canonical_id, "type": kind,
                    "title": str(detail.get("title") or entry.get("title") or ""),
                    "year": str(detail.get("year") or entry.get("year"))
                        if (detail.get("year") or entry.get("year")) is not None else None,
                    "aliases": detail.get("aliases", []) if isinstance(detail.get("aliases"), list) else [],
                    "external_ids": {"tmdb": tmdb_id or None, "imdb": imdb_id or None},
                    "overview": str(detail.get("overview")) if detail.get("overview") is not None else None,
                    "genres": detail.get("genres", []) if isinstance(detail.get("genres"), list) else [],
                    "poster_url": detail.get("poster_url"), "sources": streams,
                    "provider_refs": detail.get("provider_refs", [])
                        if isinstance(detail.get("provider_refs"), list) else [],
                    "seasons": normalized_seasons, "provenance": record_provenance,
                    "legacy_ids": [str(entry["id"])], "catalog_sections": [section], "raw": raw,
                    "identity_resolution": {
                        "strategy": (
                            "tmdb_type_year_language" if "|tmdb:" in identity_key and "|legacy:" not in identity_key else
                            "imdb_type_year_language" if "|imdb:" in identity_key and "|legacy:" not in identity_key else
                            "legacy_id_provider_id_without_year" if ("|tmdb:" in identity_key or "|imdb:" in identity_key) else
                            "legacy_id_title_year_language"
                        ),
                        "provider": "tmdb" if "|tmdb:" in identity_key else "imdb" if "|imdb:" in identity_key else None,
                        "external_id": tmdb_id if "|tmdb:" in identity_key else imdb_id if "|imdb:" in identity_key else None,
                        "media_type": kind,
                        "year": str(detail.get("year") or entry.get("year") or "").strip() or None,
                        "confidence": "high" if ("|tmdb:" in identity_key or "|imdb:" in identity_key)
                                      and "|legacy:" not in identity_key else "conservative",
                        "legacy_id_conflict": len(keys_by_legacy_id[str(entry["id"])]) > 1,
                    },
                }
                if override_info:
                    record["identity_resolution"]["identity_override"] = override_info
                    record["identity_resolution"]["identity_overrides"] = [override_info]
                if identity_key in aggregate_keys:
                    current = aggregated.get(identity_key)
                    if current is None:
                        aggregated[identity_key] = record
                    else:
                        _merge_vod_records(current, record)
                else:
                    output_records += 1
                    yield record

    for identity_key in sorted(aggregated, key=lambda key: final_ids[key]):
        output_records += 1
        yield aggregated[identity_key]
    identity_report["output_records"] = output_records


def parse_vod_catalog(root: Path, source_id: str = "catalog-existing") -> tuple[list, list]:
    quarantine = []
    records = list(iter_vod_catalog(root, source_id, quarantine))
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


def parse_epg_channel_index(document: dict, source_ref: str = "catalog/epg/xmltv-channels.json") -> tuple[list, list]:
    """Normalize the repository-owned compact XMLTV channel index without network access."""
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True)
    records, quarantine = [], []
    sources = document.get("sources", {}) if isinstance(document, dict) else {}
    if not isinstance(sources, dict):
        return [], [{"domain": "epg", "reason": "invalid_xmltv_channel_sources", "raw": sources}]
    for source_id, source in sorted(sources.items()):
        if not isinstance(source, dict):
            quarantine.append({"domain": "epg", "reason": "invalid_xmltv_source", "source_id": source_id, "raw": source})
            continue
        provenance = input_provenance(str(source_id), "xmltv-channel-index-json", payload, source_ref)
        channels = source.get("channels", [])
        if not isinstance(channels, list):
            quarantine.append({"domain": "epg", "reason": "invalid_xmltv_channel_list", "source_id": source_id, "raw": channels})
            continue
        seen = set()
        for channel in channels:
            if not isinstance(channel, dict) or not str(channel.get("id") or "").strip():
                quarantine.append({"domain": "epg", "reason": "missing_xmltv_channel_id", "source_id": source_id, "raw": channel})
                continue
            provider_id = str(channel["id"]).strip()
            if provider_id in seen:
                quarantine.append({"domain": "epg", "reason": "duplicate_xmltv_channel_id", "source_id": source_id,
                                   "provider_channel_id": provider_id, "raw": channel})
                continue
            seen.add(provider_id)
            names = channel.get("display_names", [])
            if not isinstance(names, list):
                names = []
            names = list(dict.fromkeys(str(name).strip() for name in names if str(name).strip()))
            if not names:
                quarantine.append({"domain": "epg", "reason": "missing_xmltv_display_name", "source_id": source_id,
                                   "provider_channel_id": provider_id, "raw": channel})
            records.append({
                "id": stable_id("epgchannel", str(source_id), provider_id),
                "provider_channel_id": provider_id,
                "display_names": names,
                "source_id": str(source_id),
                "fetched_at": source.get("fetched_at"),
                "provenance": [provenance],
                "raw": {"source": source, "channel": channel},
            })
        declared_count = source.get("channel_count")
        if isinstance(declared_count, int) and declared_count != len(channels):
            quarantine.append({"domain": "epg", "reason": "xmltv_channel_count_mismatch",
                               "source_id": source_id, "declared": declared_count, "actual": len(channels)})
    return records, quarantine


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
