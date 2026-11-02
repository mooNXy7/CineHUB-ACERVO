#!/usr/bin/env python3
"""Build conservative, read-only channel source candidates from SaimoPlayer/catalogo.txt."""
from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_QUERY = {
    "token", "access_token", "auth", "authorization", "password", "passwd",
    "username", "user", "key", "signature", "sig", "session", "expires", "hash",
}
CREDENTIAL_PATH = re.compile(r"/(?:live|movie|series|timeshift)/[^/]{3,}/[^/]{3,}/", re.I)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _decoded_relay_contains_credentials(path: str) -> bool:
    match = re.search(r"/relay/m/([A-Za-z0-9_-]{24,})", path, re.I)
    if not match:
        return False
    token = match.group(1)
    try:
        decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8", "ignore")
    except (ValueError, base64.binascii.Error):
        return False
    return bool(re.search(
        r"https?://[^/]+/(?:live|movie|series|timeshift)/[^/]+/[^/]+/",
        decoded, re.I
    ))


def safe_reference_stream(raw: str) -> tuple[bool, str]:
    """Reject non-HTTPS, credential-bearing, private, tokenized and encoded IPTV URLs."""
    try:
        parsed = urlsplit(str(raw or "").strip())
        if parsed.scheme.casefold() != "https" or not parsed.hostname:
            return False, "not_https"
        if parsed.username is not None or parsed.password is not None:
            return False, "embedded_credentials"
        if parsed.port not in (None, 443):
            return False, "nonstandard_port"
        host = parsed.hostname.rstrip(".").casefold()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False, "private_host"
        try:
            ip = ipaddress.ip_address(host)
            if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                    or ip.is_multicast or ip.is_unspecified):
                return False, "private_host"
        except ValueError:
            pass
        if any(key.casefold() in SENSITIVE_QUERY for key, _ in parse_qsl(parsed.query)):
            return False, "sensitive_query"
        if CREDENTIAL_PATH.search(parsed.path):
            return False, "credential_path"
        if _decoded_relay_contains_credentials(parsed.path):
            return False, "encoded_credential_path"
        # Long opaque hex path segments are commonly expiring access keys.
        if any(re.fullmatch(r"[a-f0-9]{16,}", part, re.I)
               for part in parsed.path.split("/") if part):
            return False, "opaque_path_token"
        return True, "eligible_unverified"
    except (TypeError, ValueError):
        return False, "invalid_url"


def parse_catalogo(path: Path) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None
    last_source: dict | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^\s*([^:#][^:]*):\s*(.*)$", raw)
        if not match:
            continue
        key, value = match.group(1).strip().casefold(), match.group(2).strip()
        if key == "canal":
            if current:
                blocks.append(current)
            current = {"name": value, "category": None, "logo_url": None,
                       "sources": [], "referer": None, "user_agent": None}
            last_source = None
        elif current is None:
            continue
        elif key == "categoria":
            current["category"] = value or None
        elif key == "logo":
            current["logo_url"] = value or None
        elif key == "fonte":
            last_source = {"url": value, "quality": None, "source_order": len(current["sources"]) + 1}
            current["sources"].append(last_source)
        elif key == "qualidade" and last_source is not None:
            last_source["quality"] = value or None
        elif key == "referer":
            current["referer"] = value or None
        elif key in {"agente", "user-agent", "user_agent"}:
            current["user_agent"] = value or None
    if current:
        blocks.append(current)
    return blocks


def build_report(channels_path: Path, reference_file: Path, output: Path) -> dict:
    catalog = json.loads(channels_path.read_text(encoding="utf-8"))
    channels = catalog.get("channels", [])
    by_name: dict[str, list[dict]] = {}
    for channel in channels:
        if isinstance(channel, dict) and channel.get("name"):
            by_name.setdefault(normalize(channel["name"]), []).append(channel)

    counts = {
        "reference_channel_blocks": 0, "exact_unique_matches": 0,
        "ambiguous_matches": 0, "unmatched_reference_blocks": 0,
        "matched_channels_without_streams": 0, "channels_with_candidates": 0,
        "eligible_unverified_urls": 0, "rejected_urls": 0,
        "channels_with_existing_streams": 0, "missing_logo_candidates": 0,
    }
    candidates = []
    rejected = []
    for block in parse_catalogo(reference_file):
        counts["reference_channel_blocks"] += 1
        matches = by_name.get(normalize(block["name"]), [])
        if len(matches) != 1:
            key = "ambiguous_matches" if len(matches) > 1 else "unmatched_reference_blocks"
            counts[key] += 1
            continue
        counts["exact_unique_matches"] += 1
        target = matches[0]
        if target.get("sources"):
            counts["channels_with_existing_streams"] += 1
            continue
        counts["matched_channels_without_streams"] += 1
        safe_sources = []
        for source in block["sources"]:
            ok, reason = safe_reference_stream(source["url"])
            if not ok:
                counts["rejected_urls"] += 1
                if len(rejected) < 100:
                    rejected.append({"channel_id": target.get("id"), "reason": reason,
                                     "source_order": source["source_order"]})
                continue
            parsed = urlsplit(source["url"])
            source_type = ("hls" if parsed.path.casefold().endswith(".m3u8")
                           else "dash" if parsed.path.casefold().endswith(".mpd")
                           else "indirect_or_unknown")
            headers = {}
            if block.get("referer"):
                ref_ok, _ = safe_reference_stream(block["referer"])
                if ref_ok:
                    headers["referer"] = block["referer"]
            agent = block.get("user_agent")
            if agent and len(agent) <= 512 and not re.search(r"[\r\n]", agent):
                headers["user_agent"] = agent
            safe_sources.append({
                "url": source["url"], "host": parsed.hostname,
                "source_type": source_type, "quality": source["quality"],
                "source_order": source["source_order"], "headers": headers,
                "status": "eligible_unverified",
            })
            counts["eligible_unverified_urls"] += 1
        if not target.get("logo_url") and block.get("logo_url"):
            logo_ok, _ = safe_reference_stream(block["logo_url"])
            if logo_ok:
                counts["missing_logo_candidates"] += 1
        if safe_sources:
            counts["channels_with_candidates"] += 1
            candidates.append({
                "channel_id": target.get("id"), "channel_name": target.get("name"),
                "category": target.get("group"), "reference_category": block.get("category"),
                "sources": safe_sources,
                "logo_candidate": block.get("logo_url") if not target.get("logo_url") else None,
                "requires_network_probe_before_import": True,
                "automatic_update": False,
            })

    report = {
        "schema_version": 1, "report_type": "review_only_catalogo_channel_source_candidates",
        "read_only": True, "catalog_mutated": False,
        "source": "authorized SaimoPlayer/catalogo.txt",
        "matching": "exact normalized channel name only; no fuzzy matching",
        "policy": [
            "Only channels already present in CineHUB and without a stream are considered.",
            "Only HTTPS sources without embedded credentials, sensitive query keys, private hosts, credential paths, encoded IPTV credentials, or opaque hex path tokens are listed.",
            "Source order is preserved; headers are included only when safe.",
            "Candidates are not active playback sources until a separate network probe and review succeeds.",
            "Existing channel streams, metadata, EPG associations, and playback settings are never changed.",
        ],
        "counts": counts, "candidates": candidates, "rejected_examples": rejected,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels", type=Path, default=ROOT / "catalog/channels/channels.json")
    parser.add_argument("--reference-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/catalogo-channel-source-candidates.json")
    args = parser.parse_args()
    report = build_report(args.channels, args.reference_file, args.output)
    print(json.dumps({"counts": report["counts"], "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
