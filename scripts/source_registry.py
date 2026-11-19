#!/usr/bin/env python3
"""Central source registry, URL policy, and format adapter dispatch for ACERVO V3."""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "sources" / "sources.json"
DOMAINS = {"vod", "channels", "radios", "epg", "logos"}
FORMATS = {"m3u", "json", "txt", "xmltv", "vod_catalog"}
SENSITIVE_QUERY_KEYS = {
    "access_token", "api_key", "apikey", "auth", "authorization", "cookie",
    "key", "password", "passwd", "secret", "signature", "token", "client_secret",
    "client_id_secret", "session", "sig", "x_api_key",
}


def validate_source_url(value: object, *, allow_http: bool = True) -> tuple[bool, str]:
    """Validate a public HTTP(S) source URL without fetching it.

    DNS resolution is deliberately separate: callers must validate every resolved
    address immediately before making a request to defend against DNS rebinding.
    """
    if not isinstance(value, str) or not value.strip():
        return False, "missing_url"
    try:
        parsed = urlsplit(value.strip())
        scheme = parsed.scheme.casefold()
        if scheme not in ({"https", "http"} if allow_http else {"https"}):
            return False, "unsupported_scheme"
        if not parsed.hostname:
            return False, "missing_host"
        _ = parsed.port  # Force validation of malformed/out-of-range ports.
        if parsed.username is not None or parsed.password is not None:
            return False, "embedded_credentials"
        host = parsed.hostname.rstrip(".").casefold()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
            return False, "local_hostname"
        if "%" in host:
            return False, "scoped_or_encoded_host"
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (not address.is_global or address.is_multicast):
            return False, "non_public_ip"
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
            if key.casefold() in SENSITIVE_QUERY_KEYS:
                return False, "sensitive_query_parameter"
        if parsed.fragment:
            return False, "url_fragment_not_allowed"
        return True, "ok"
    except (TypeError, ValueError):
        return False, "malformed_url"


def validate_resolved_addresses(addresses: list[str]) -> tuple[bool, str]:
    """Reject DNS answers containing any non-public address before network access."""
    if not addresses:
        return False, "no_resolved_addresses"
    for raw in addresses:
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            return False, "invalid_resolved_address"
        if not address.is_global or address.is_multicast:
            return False, "resolved_non_public_address"
    return True, "ok"



def redact_sensitive(value: object) -> object:
    """Return a JSON-safe copy with credential-like fields and URL query values redacted."""
    sensitive = {"access_token", "api_key", "apikey", "auth", "authorization",
                 "client_secret", "cookie", "key", "password", "passwd",
                 "secret", "session", "signature", "sig", "token"}
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if str(key).casefold().replace("-", "_") in sensitive
            else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str) and value.strip().lower().startswith(("http://", "https://")):
        try:
            parsed = urlsplit(value)
            host = parsed.hostname or ""
            if parsed.username is not None or parsed.password is not None:
                host = "[REDACTED]@" + host
            query = []
            for key, item in parse_qsl(parsed.query, keep_blank_values=True):
                query.append((key, "[REDACTED]" if key.casefold().replace("-", "_") in sensitive else item))
            from urllib.parse import urlencode, urlunsplit
            netloc = host
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunsplit((parsed.scheme, netloc, parsed.path, urlencode(query), parsed.fragment))
        except ValueError:
            return "[REDACTED_URL]"
    return value


def normalize_source(item: object) -> tuple[dict | None, str | None]:
    if not isinstance(item, dict):
        return None, "source_must_be_object"
    source_id = item.get("id")
    if not isinstance(source_id, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{1,127}", source_id):
        return None, "invalid_source_id"
    domain = str(item.get("domain") or item.get("category") or "").casefold()
    domain = {"channel": "channels", "radio": "radios"}.get(domain, domain)
    if domain not in DOMAINS:
        return None, "unsupported_domain"
    source_format = str(item.get("format") or "").casefold()
    if source_format not in FORMATS:
        return None, "unsupported_format"
    origin = item.get("origin")
    if origin is None and item.get("url"):
        origin = {"kind": "url", "value": item["url"]}
    if not isinstance(origin, dict) or origin.get("kind") not in {"url", "repository_path"}:
        return None, "invalid_origin"
    origin_value = origin.get("value")
    if not isinstance(origin_value, str) or not origin_value.strip():
        return None, "missing_origin_value"
    if origin["kind"] == "url":
        valid, reason = validate_source_url(origin_value)
        if not valid:
            return None, reason
    else:
        path = Path(origin_value)
        if path.is_absolute() or ".." in path.parts or "\\" in origin_value or chr(0) in origin_value:
            return None, "unsafe_repository_path"
    if origin["kind"] == "url" and item.get("url") and item["url"] != origin_value:
        return None, "origin_url_mismatch"
    enabled_value = item.get("enabled", False)
    if not isinstance(enabled_value, bool):
        return None, "enabled_must_be_boolean"
    credentials_ref = item.get("credentials_ref")
    if credentials_ref is not None and (
        not isinstance(credentials_ref, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", credentials_ref)
    ):
        return None, "invalid_credentials_ref"
    error_history = item.get("error_history", [])
    if not isinstance(error_history, list):
        return None, "invalid_error_history"
    authorization = item.get("authorization")
    if not isinstance(authorization, dict):
        authorization = {
            "status": "unverified",
            "terms": item.get("license"),
            "notes": item.get("notes"),
        }
    status = str(item.get("status") or ("active" if item.get("enabled", False) else "disabled")).casefold()
    if status not in {"active", "disabled", "quarantined", "degraded", "pending_review"}:
        return None, "invalid_status"
    try:
        priority = int(item.get("priority", 100))
    except (TypeError, ValueError):
        return None, "invalid_priority"
    if not -10000 <= priority <= 10000:
        return None, "priority_out_of_range"
    return {
        "id": source_id,
        "name": str(item.get("name") or source_id),
        "provider": str(item.get("provider") or item.get("name") or source_id),
        "domain": domain,
        "format": source_format,
        "origin": {"kind": origin["kind"], "value": origin_value.strip()},
        "url": origin_value.strip() if origin["kind"] == "url" else None,
        "priority": priority,
        "language": item.get("language"),
        "region": item.get("region"),
        "authorization": authorization,
        "enabled": enabled_value and status == "active",
        "status": status,
        "update_frequency": item.get("update_frequency", "manual"),
        "last_processed_at": item.get("last_processed_at"),
        "last_error": item.get("last_error"),
        "error_history": error_history,
        "credentials_ref": credentials_ref,
        "adapter": item.get("adapter"),
        "options": item.get("options", {}),
        "license": item.get("license"),
        "match_strategy": item.get("match_strategy"),
        "provenance": item.get("provenance", []),
        "raw": item,
    }, None



def resolve_local_source_path(value: str, repository_root: Path = ROOT) -> Path:
    """Resolve a repository source path and reject missing files or symlink escapes."""
    root = repository_root.resolve()
    candidate = (root / value).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("repository_path_outside_root") from exc
    if not candidate.is_file():
        raise ValueError("repository_source_not_file")
    return candidate


def load_registry(path: Path = REGISTRY_PATH) -> tuple[list[dict], list[dict]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [{"reason": "registry_read_error", "detail": str(exc)}]
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return [], [{"reason": "invalid_registry_header"}]
    raw_sources = document.get("sources")
    if not isinstance(raw_sources, list):
        return [], [{"reason": "sources_must_be_array"}]
    accepted, quarantine, seen_ids, seen_origins = [], [], set(), set()
    for index, item in enumerate(raw_sources):
        record, error = normalize_source(item)
        if error:
            quarantine.append({"index": index, "reason": error, "raw": redact_sensitive(item)})
            continue
        if record["id"] in seen_ids:
            quarantine.append({"index": index, "reason": "duplicate_source_id", "raw": redact_sensitive(item)})
            continue
        origin = record["origin"]
        value = origin["value"]
        if origin["kind"] == "repository_path":
            try:
                resolve_local_source_path(value)
            except (OSError, ValueError):
                quarantine.append({"index": index, "reason": "repository_source_missing_or_unsafe",
                                   "raw": redact_sensitive(item)})
                continue
        if origin["kind"] == "url":
            parsed = urlsplit(value)
            host = (parsed.hostname or "").casefold()
            port = parsed.port
            default_port = (parsed.scheme.casefold() == "https" and port == 443) or (
                parsed.scheme.casefold() == "http" and port == 80
            )
            authority = host if port is None or default_port else f"{host}:{port}"
            value = f"{parsed.scheme.casefold()}://{authority}{parsed.path or '/'}"
            if parsed.query:
                value += f"?{parsed.query}"
        else:
            value = Path(value).as_posix()
        fingerprint = (record["domain"], record["format"], value)
        if fingerprint in seen_origins:
            quarantine.append({"index": index, "reason": "duplicate_source_origin", "raw": redact_sensitive(item)})
            continue
        seen_ids.add(record["id"])
        seen_origins.add(fingerprint)
        record["raw"] = redact_sensitive(record["raw"])
        accepted.append(record)
    accepted.sort(key=lambda source: (source["priority"], source["id"]))
    return accepted, quarantine


def parse_source_payload(source: dict, payload: bytes | str | Path | None = None, *, source_ref: str | None = None,
                         repository_root: Path | None = None):
    """Dispatch to a format adapter; parsing remains offline and never follows source URLs."""
    from acervo_v2.importers import (
        parse_channels_json, parse_m3u, parse_radios_json, parse_radios_text,
        parse_vod_reference_movies, parse_vod_reference_series, parse_vod_catalog,
    )
    from acervo_v2.xmltv import parse_xmltv

    source_id = source["id"]
    ref = source_ref or source.get("origin", {}).get("value", source_id)
    fmt, domain = source["format"], source["domain"]
    root = repository_root or ROOT
    origin = source.get("origin") or {}
    if fmt == "vod_catalog":
        if origin.get("kind") != "repository_path" or origin.get("value") != "catalog/vod/index.json":
            raise ValueError("VOD catalog source must reference catalog/vod/index.json")
        resolve_local_source_path(origin["value"], Path(root))
        return parse_vod_catalog(Path(root), source_id)
    if payload is None:
        if origin.get("kind") != "repository_path":
            raise ValueError("remote source payload must be supplied by a controlled fetcher")
        payload = resolve_local_source_path(origin["value"], Path(root)).read_bytes()
    text = payload.read_bytes() if isinstance(payload, Path) else payload
    text = text.decode("utf-8-sig") if isinstance(text, bytes) and fmt != "xmltv" else text
    if fmt == "m3u":
        if not isinstance(text, str):
            raise TypeError("M3U payload must be text")
        return parse_m3u(text, source_id, ref)
    if fmt == "xmltv":
        return parse_xmltv(payload, source_id, ref)
    if fmt == "txt":
        adapter = source.get("adapter")
        if adapter == "vod_movies":
            return parse_vod_reference_movies(str(text), source_id, ref)
        if adapter == "vod_series":
            return parse_vod_reference_series(str(text), source_id, ref)
        if domain == "radios":
            return parse_radios_text(str(text), source_id, ref)
        raise ValueError("TXT source requires a supported explicit adapter")
    if fmt == "json":
        document = json.loads(text)
        if not isinstance(document, dict):
            raise ValueError("JSON source root must be an object")
        if domain == "channels":
            return parse_channels_json(document, source_id)
        if domain == "radios":
            return parse_radios_json(document, source_id)
        if domain == "epg":
            from acervo_v2.importers import parse_epg_channel_index, parse_epg_mapping, parse_epg_sources
            if "sources" in document and isinstance(document["sources"], dict):
                return parse_epg_channel_index(document, ref)
            return parse_epg_sources(document, source_id)
        records = document.get("records", document.get("items", []))
        if not isinstance(records, list):
            raise ValueError("JSON source must contain a records or items array")
        return records, []
    raise ValueError("No adapter registered for format")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--json", action="store_true", help="print normalized registry as JSON")
    args = parser.parse_args()
    records, quarantine = load_registry(args.registry)
    if args.json:
        print(json.dumps({"schema_version": 1, "domain": "sources",
                          "records": records, "quarantine": quarantine},
                         ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in records:
            print(f"{item['id']}\t{item['status']}\t{item['domain']}\t{item['format']}\t{item['priority']}")
        print(f"accepted={len(records)} quarantined={len(quarantine)}")
    return 1 if quarantine else 0


if __name__ == "__main__":
    raise SystemExit(main())
