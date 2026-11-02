#!/usr/bin/env python3
"""Apply live-verified logo-only records from the authorized iptv-org logos API."""
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
    "a e": "a and e", "aand e": "a and e",
    "globo news": "globonews", "record news": "recordnews",
    "tv brasil": "tvbrasil", "rede tv": "redetv",
}


def normalize(value: Any) -> str:
    value = str(value or "")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = re.sub(r"\.[a-z]{2}$", "", value, flags=re.I)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = QUALITY.sub(" ", value)
    return re.sub(r"[^a-z0-9+]+", " ", value.casefold()).strip()


def match_key(value: Any) -> str:
    key = re.sub(r"\s+", " ", normalize(value)).strip()
    return ALIASES.get(key, key)


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


def parse_reference(path: Path) -> dict[str, set[str]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("iptv-org logos reference must be a JSON array")
    by_name: dict[str, set[str]] = defaultdict(set)
    for item in records:
        if not isinstance(item, dict) or item.get("in_use") is not True or item.get("feed") not in (None, ""):
            continue
        channel_id = str(item.get("channel") or "").strip()
        url = str(item.get("url") or "").strip()
        key = match_key(channel_id)
        if key and url and safe_https_image_url(url):
            by_name[key].add(url)
    return by_name


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
            needed.add(match_key(channel.get("name")))

    candidates: dict[str, str] = {}
    ambiguous = 0
    unmatched = 0
    for key in needed:
        urls = reference.get(key, set())
        if len(urls) == 1:
            candidates[key] = next(iter(urls))
        elif len(urls) > 1:
            ambiguous += 1
        else:
            unmatched += 1

    unique_urls = sorted(set(candidates.values()))
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(verify_image, unique_urls))
    live = dict(zip(unique_urls, results))

    applied = []
    invalid = 0
    for channel in eligible:
        key = match_key(channel.get("name"))
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
        "report_type": "iptv_org_logo_application",
        "catalog_mutated": bool(applied),
        "reference_channel_keys": len(reference),
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
