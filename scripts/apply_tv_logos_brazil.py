#!/usr/bin/env python3
"""Apply logos from authorized Brazil and international tv-logos GitHub indexes."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = "catalog/channels/channels.json"
ALLOWED_COUNTRIES = {"brazil", "international", "united-states", "world-latin-america"}
ALLOWED_HOST = "raw.githubusercontent.com"
IMAGE_SUFFIXES = (".png", ".svg", ".webp", ".jpg", ".jpeg")
QUALITY = re.compile(r"\b(?:hd|sd|fhd|uhd|4k|1080p|720p|h265|hevc)\b", re.I)

# Explicit spelling/brand aliases only; no fuzzy or edit-distance matching.
ALIASES = {
    "a e": "a and e",
    "arte 1": "arte1",
    "globo news": "globonews",
    "globo news hd": "globonews",
}


def normalize(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def match_key(value: Any) -> str:
    key = re.sub(r"\s+", " ", QUALITY.sub(" ", normalize(value))).strip()
    return ALIASES.get(key, key)


def safe_logo_entry(item: Any) -> tuple[str, str] | None:
    if not isinstance(item, dict):
        return None
    path = str(item.get("path") or "")
    name = str(item.get("name") or Path(path).name)
    url = str(item.get("download_url") or "").strip()
    parts = path.split("/")
    if (len(parts) < 3 or parts[0] != "countries" or parts[1] not in ALLOWED_COUNTRIES
            or not name.lower().endswith(IMAGE_SUFFIXES)):
        return None
    try:
        if int(item.get("size") or 0) <= 0:
            return None
    except (TypeError, ValueError):
        return None
    parsed = urlsplit(url)
    expected_prefix = f"/tv-logo/tv-logos/main/countries/{parts[1]}/"
    if (parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST
            or not parsed.path.startswith(expected_prefix)):
        return None
    stem = Path(name).stem
    for suffix in ("-br", "-int", "-us", "-lam", "-lat"):
        if stem.lower().endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    key = match_key(stem.replace("-", " "))
    return (key, url) if key else None


def apply(root: Path, index_file: Path) -> dict[str, Any]:
    catalog_path = root / CHANNELS_FILE
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    channels = catalog.get("channels", []) if isinstance(catalog, dict) else None
    if not isinstance(channels, list):
        raise ValueError("Channel catalog must contain a channels array")
    entries = json.loads(index_file.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("tv-logos index must be a JSON array")

    logos: dict[str, set[str]] = defaultdict(set)
    for item in entries:
        safe = safe_logo_entry(item)
        if safe:
            logos[safe[0]].add(safe[1])

    applied = []
    ambiguous = 0
    missing = 0
    skipped_existing = 0
    unmatched_sample = []
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        if str(channel.get("logo_url") or "").strip():
            skipped_existing += 1
            continue
        key = match_key(channel.get("name"))
        candidates = logos.get(key, set())
        if len(candidates) == 1:
            url = next(iter(candidates))
            channel["logo_url"] = url
            applied.append({"channel_id": str(channel.get("id") or ""),
                            "channel_name": str(channel.get("name") or ""), "logo_url": url})
        elif len(candidates) > 1:
            ambiguous += 1
        else:
            missing += 1
            if len(unmatched_sample) < 100:
                unmatched_sample.append({"channel_id": str(channel.get("id") or ""), "channel_name": str(channel.get("name") or "")})

    if applied:
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "report_type": "tv_logos_brazil_application",
        "catalog_mutated": bool(applied),
        "source_files_listed": len(entries),
        "unique_logo_keys": len(logos),
        "applied": len(applied),
        "ambiguous": ambiguous,
        "no_verified_source_match": missing,
        "unmatched_sample": unmatched_sample,
        "skipped_existing": skipped_existing,
        "updated_channels": applied,
        "matching_policy": "Unique exact normalized brand or explicit alias; quality markers removed; existing logos untouched.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--logo-index-file", type=Path, required=True)
    args = parser.parse_args()
    result = apply(args.root, args.logo_index_file)
    print(json.dumps({key: value for key, value in result.items() if key != "updated_channels"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
