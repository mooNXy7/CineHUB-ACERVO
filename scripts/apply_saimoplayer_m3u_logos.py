#!/usr/bin/env python3
"""Apply live-verified logo fields from SaimoPlayer's M3U without importing streams."""
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
ATTR = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
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


def parse_m3u(path: Path) -> dict[str, set[str]]:
    by_name: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.startswith("#EXTINF:"):
                continue
            attrs = {key.casefold(): value for key, value in ATTR.findall(line)}
            logo = attrs.get("tvg-logo", "").strip()
            if not logo:
                continue
            display = line.split(",", 1)[1].strip() if "," in line else ""
            names = {attrs.get("tvg-name", "").strip(), attrs.get("tvg-id", "").strip(), display}
            for name in names:
                key = canonical_key(name)
                if key:
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


def apply(root: Path, m3u_file: Path,
          verify_image: Callable[[str], bool] = is_live_image_url) -> dict[str, Any]:
    catalog_path = root / CHANNELS_FILE
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    channels = catalog.get("channels", []) if isinstance(catalog, dict) else None
    if not isinstance(channels, list):
        raise ValueError("Channel catalog must contain a channels array")
    source = parse_m3u(m3u_file)

    eligible = []
    needed_keys = set()
    skipped_existing = 0
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        if str(channel.get("logo_url") or "").strip():
            skipped_existing += 1
        else:
            eligible.append(channel)
            needed_keys.add(canonical_key(channel.get("name")))

    url_candidates = set()
    ambiguous = 0
    no_match = 0
    for key in needed_keys:
        values = source.get(key, set())
        if len(values) == 1:
            url = next(iter(values))
            if safe_https_image_url(url):
                url_candidates.add(url)
        elif len(values) > 1:
            ambiguous += 1
        else:
            no_match += 1

    verified: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(verify_image, sorted(url_candidates)))
    verified.update(zip(sorted(url_candidates), results))

    applied = []
    invalid = 0
    for channel in eligible:
        key = canonical_key(channel.get("name"))
        values = source.get(key, set())
        if len(values) != 1:
            continue
        url = next(iter(values))
        if not verified.get(url, False):
            invalid += 1
            continue
        channel["logo_url"] = url
        applied.append({"channel_id": str(channel.get("id") or ""),
                        "channel_name": str(channel.get("name") or ""), "logo_url": url})

    if applied:
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "report_type": "saimoplayer_m3u_logo_application",
        "catalog_mutated": bool(applied),
        "source_name_keys": len(source),
        "source_logo_urls_probed": len(url_candidates),
        "verified_image_urls": sum(verified.values()),
        "applied": len(applied),
        "ambiguous_source_keys": ambiguous,
        "unmatched_catalog_keys": no_match,
        "invalid_or_unreachable_images": invalid,
        "skipped_existing": skipped_existing,
        "updated_channels": applied,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--m3u-file", type=Path, required=True)
    args = parser.parse_args()
    result = apply(args.root, args.m3u_file)
    print(json.dumps({key: value for key, value in result.items() if key != "updated_channels"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
