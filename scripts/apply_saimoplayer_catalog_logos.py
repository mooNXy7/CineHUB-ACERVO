#!/usr/bin/env python3
"""Apply only live-verified logo fields from the authorized SaimoPlayer channel catalog.

Only 'canal' and 'logo' fields are read. Stream, referer, agent and key fields
are deliberately ignored.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qsl, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = "catalog/channels/channels.json"
SENSITIVE_QUERY_KEYS = {"token", "access_token", "auth", "authorization", "key",
                        "password", "passwd", "signature", "sig", "session"}
QUALITY = re.compile(r"\\b(?:hd|sd|fhd|uhd|4k|1080p|720p|h265|hevc)\\b", re.I)

# Alias table taken from the authorized SaimoPlayer channel canonicalizer.
ALIASES = {
    "warner channel": "warner",
    "canal sony": "sony channel",
    "discovery h h": "discovery home health",
    "h2": "history 2",
    "id": "discovery id",
    "off": "canal off",
    "cultura": "tv cultura",
    "pai eterno": "tv pai eterno",
    "tv cancao nova": "cancao nova",
    "recordtv rj": "record rj",
    "recordtv sp": "record sp",
    "recordtv goias": "record go",
    "sbt tv alterosa": "sbt alterosa",
    "globo brasilia": "globo df",
    "globo minas": "globo mg",
    "caze tv": "cazetv 1",
    "dazn 1": "dazn jogo 1",
    "dazn 2": "dazn jogo 2",
    "paramount 1": "paramount jogo 1",
    "paramount 2": "paramount jogo 2",
    "paramount 3": "paramount jogo 3",
    "canal goat 2": "canal goat jogo 2",
}


def normalize(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"^24\\s*h\\s*", "", value, flags=re.I)
    value = QUALITY.sub(" ", value)
    return re.sub(r"[^a-z0-9+]+", " ", value.casefold()).strip()


def canonical_key(value: Any) -> str:
    key = re.sub(r"\\s+", " ", normalize(value)).strip()
    return ALIASES.get(key, key)


def parse_catalog(path: Path) -> dict[str, set[str]]:
    by_name: dict[str, set[str]] = defaultdict(set)
    current_name = ""
    current_logo = ""
    def flush() -> None:
        if current_name and current_logo:
            by_name[canonical_key(current_name)].add(current_logo)
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("canal:"):
            flush()
            current_name = line.split(":", 1)[1].strip()
            current_logo = ""
        elif line.lower().startswith("logo:") and not current_logo:
            current_logo = line.split(":", 1)[1].strip()
    flush()
    return by_name


def safe_https_image_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if any(key.casefold() in SENSITIVE_QUERY_KEYS for key, _ in parse_qsl(parsed.query)):
            return False
        host = parsed.hostname.casefold().rstrip(".")
        return host not in {"localhost", "localhost.localdomain"} and not host.endswith(".local")
    except ValueError:
        return False


def is_live_image_url(url: str, timeout: float = 6.0) -> bool:
    if not safe_https_image_url(url):
        return False
    for method in ("HEAD", "GET"):
        try:
            request = Request(url, headers={"User-Agent": "CineHUB-Logo-Validator/1.0",
                                            "Range": "bytes=0-255"}, method=method)
            with urlopen(request, timeout=timeout) as response:
                final = urlsplit(response.geturl())
                content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
                if final.scheme == "https" and content_type.startswith("image/"):
                    return True
                return False
        except Exception:
            continue
    return False


def apply(root: Path, source_file: Path,
          verify_image: Callable[[str], bool] = is_live_image_url) -> dict[str, Any]:
    catalog_path = root / CHANNELS_FILE
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    channels = catalog.get("channels", []) if isinstance(catalog, dict) else None
    if not isinstance(channels, list):
        raise ValueError("Channel catalog must contain a channels array")

    source = parse_catalog(source_file)
    verified_cache: dict[str, bool] = {}
    applied = []
    ambiguous = 0
    invalid = 0
    no_match = 0
    skipped_existing = 0
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        if str(channel.get("logo_url") or "").strip():
            skipped_existing += 1
            continue
        candidates = source.get(canonical_key(channel.get("name")), set())
        if len(candidates) > 1:
            ambiguous += 1
            continue
        if not candidates:
            no_match += 1
            continue
        url = next(iter(candidates))
        if url not in verified_cache:
            verified_cache[url] = safe_https_image_url(url) and bool(verify_image(url))
        if not verified_cache[url]:
            invalid += 1
            continue
        channel["logo_url"] = url
        applied.append({"channel_id": str(channel.get("id") or ""),
                        "channel_name": str(channel.get("name") or ""), "logo_url": url})

    if applied:
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "report_type": "saimoplayer_channel_logo_application",
        "catalog_mutated": bool(applied),
        "source_channels_with_logos": sum(bool(urls) for urls in source.values()),
        "applied": len(applied),
        "ambiguous_source_matches": ambiguous,
        "unmatched_catalog_channels": no_match,
        "invalid_or_unreachable_images": invalid,
        "skipped_existing": skipped_existing,
        "verified_unique_urls": sum(verified_cache.values()),
        "updated_channels": applied,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source-file", type=Path, required=True)
    args = parser.parse_args()
    result = apply(args.root, args.source_file)
    print(json.dumps({key: value for key, value in result.items() if key != "updated_channels"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
