#!/usr/bin/env python3
"""Apply live-verified logo-only fields from the authorized SaimoTV-Android reference."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qsl, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = "catalog/channels/channels.json"
SENSITIVE_QUERY_KEYS = {"token", "access_token", "auth", "authorization", "key",
                        "password", "passwd", "signature", "sig", "session"}
QUALITY = re.compile(r"\b(?:hd|sd|fhd|uhd|4k|1080p|720p|h265|hevc)\b", re.I)
ALIASES = {
    "warner channel": "warner", "canal sony": "sony channel",
    "discovery h h": "discovery home health", "h2": "history 2",
    "id": "discovery id", "off": "canal off", "cultura": "tv cultura",
    "pai eterno": "tv pai eterno", "tv cancao nova": "cancao nova",
    "recordtv rj": "record rj", "recordtv sp": "record sp",
    "recordtv goias": "record go", "sbt tv alterosa": "sbt alterosa",
    "globo brasilia": "globo df", "globo minas": "globo mg",
    "caze tv": "cazetv 1", "dazn 1": "dazn jogo 1",
    "dazn 2": "dazn jogo 2", "paramount 1": "paramount jogo 1",
    "paramount 2": "paramount jogo 2", "paramount 3": "paramount jogo 3",
    "canal goat 2": "canal goat jogo 2",
}


def normalize(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"^24\s*h\s*", "", value, flags=re.I)
    value = QUALITY.sub(" ", value)
    return re.sub(r"[^a-z0-9+]+", " ", value.casefold()).strip()


def canonical_key(value: Any) -> str:
    key = re.sub(r"\s+", " ", normalize(value)).strip()
    return ALIASES.get(key, key)


def parse_reference(path: Path) -> dict[str, set[str]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    records = document.get("data", []) if isinstance(document, dict) else None
    if not isinstance(records, list):
        raise ValueError("SaimoTV-Android offline reference must contain a data array")
    by_name: dict[str, set[str]] = defaultdict(set)
    for item in records:
        if not isinstance(item, dict):
            continue
        key = canonical_key(item.get("name"))
        logo = str(item.get("logo") or "").strip()
        if key and logo:
            by_name[key].add(logo)
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


def is_live_image_url(url: str, timeout: float = 5.0) -> bool:
    if not safe_https_image_url(url):
        return False
    for method in ("HEAD", "GET"):
        try:
            request = Request(url, headers={"User-Agent": "CineHUB-Logo-Validator/1.0",
                                            "Range": "bytes=0-255"}, method=method)
            with urlopen(request, timeout=timeout) as response:
                final = urlsplit(response.geturl())
                content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
                return final.scheme == "https" and content_type.startswith("image/")
        except Exception:
            continue
    return False


def apply(root: Path, reference_file: Path,
          verify_image: Callable[[str], bool] = is_live_image_url) -> dict[str, Any]:
    catalog_path = root / CHANNELS_FILE
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    channels = catalog.get("channels", []) if isinstance(catalog, dict) else None
    if not isinstance(channels, list):
        raise ValueError("Channel catalog must contain a channels array")
    reference = parse_reference(reference_file)

    eligible = []
    needed = set()
    skipped_existing = 0
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        if str(channel.get("logo_url") or "").strip():
            skipped_existing += 1
        else:
            eligible.append(channel)
            needed.add(canonical_key(channel.get("name")))

    candidates: dict[str, str] = {}
    ambiguous = 0
    unmatched = 0
    invalid_candidates = 0
    for key in needed:
        urls = reference.get(key, set())
        if len(urls) == 1:
            url = next(iter(urls))
            if safe_https_image_url(url):
                candidates[key] = url
            else:
                invalid_candidates += 1
        elif len(urls) > 1:
            ambiguous += 1
        else:
            unmatched += 1

    unique_urls = sorted(set(candidates.values()))
    with ThreadPoolExecutor(max_workers=16) as pool:
        live_results = list(pool.map(verify_image, unique_urls))
    live = dict(zip(unique_urls, live_results))

    applied = []
    invalid = invalid_candidates
    for channel in eligible:
        key = canonical_key(channel.get("name"))
        url = candidates.get(key)
        if not url:
            continue
        if not live.get(url, False):
            invalid += 1
            continue
        channel["logo_url"] = url
        applied.append({"channel_id": str(channel.get("id") or ""),
                        "channel_name": str(channel.get("name") or ""), "logo_url": url})

    if applied:
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "report_type": "saimotv_android_logo_application",
        "catalog_mutated": bool(applied),
        "reference_channels_with_logo": sum(bool(urls) for urls in reference.values()),
        "unique_reference_urls_checked": len(unique_urls),
        "verified_image_urls": sum(live.values()),
        "applied": len(applied),
        "ambiguous_reference_matches": ambiguous,
        "unmatched_catalog_keys": unmatched,
        "invalid_or_unreachable_images": invalid,
        "skipped_existing": skipped_existing,
        "updated_channels": applied,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reference-file", type=Path, required=True)
    args = parser.parse_args()
    result = apply(args.root, args.reference_file)
    print(json.dumps({key: value for key, value in result.items() if key != "updated_channels"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
