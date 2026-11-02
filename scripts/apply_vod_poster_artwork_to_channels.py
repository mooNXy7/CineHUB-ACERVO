#!/usr/bin/env python3
"""Fill missing 24H/channel artwork from exact VOD poster matches in the shared catalog."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = Path("catalog/channels/channels.json")
VOD_DIR = Path("catalog/vod/index")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"

try:
    from .update_catalog import atomic_write_json, safe_https_url
except ImportError:
    from update_catalog import atomic_write_json, safe_https_url


def normalize_title(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s*\(((?:19|20)\d{2})\)\s*$", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def channel_base_title(value: str) -> str:
    value = re.sub(r"^\s*\[24h\]\s*", "", value, flags=re.I)
    value = re.sub(r"\s*[-–]?\s*24h(?:\s*ultra\s*hd)?\s*$", "", value, flags=re.I)
    value = re.sub(r"\s*\[s\d{1,2}\]\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+(?:ultra\s*hd|fhd|hd|sd|uhd|4k|h265|hevc)\s*$", "", value, flags=re.I)
    return value.strip()


def extract_year(value: str) -> str:
    match = re.search(r"\(((?:19|20)\d{2})\)", value or "")
    return match.group(1) if match else ""


def resolve_poster(value: Any) -> str | None:
    poster = str(value or "").strip()
    if poster.startswith("/"):
        poster = TMDB_IMAGE_BASE + poster
    if not safe_https_url(poster):
        return None
    if (poster.split("/", 3)[2].lower() != "image.tmdb.org"):
        return None
    return poster


def build_vod_lookup(root: Path) -> dict[str, list[dict[str, str]]]:
    lookup: dict[str, list[dict[str, str]]] = defaultdict(list)
    for section in ("movies", "series", "anime", "doramas"):
        path = root / VOD_DIR / f"{section}.json"
        if not path.exists():
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError(f"VOD index must be a list: {path}")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "").strip()
            key = normalize_title(title)
            poster = resolve_poster(entry.get("poster_url"))
            if not key or not poster:
                continue
            lookup[key].append({
                "id": str(entry.get("id") or ""),
                "title": title,
                "year": str(entry.get("year") or ""),
                "poster_url": poster,
                "section": section,
            })
    return lookup


def build_report(root: Path) -> dict[str, Any]:
    channels_path = root / CHANNELS_FILE
    channel_doc = json.loads(channels_path.read_text(encoding="utf-8"))
    channels = channel_doc.get("channels", [])
    lookup = build_vod_lookup(root)
    counts = {
        "channels_examined": len(channels),
        "channels_without_logo": 0,
        "exact_title_matches": 0,
        "artwork_applied": 0,
        "ambiguous_vod_matches": 0,
        "year_conflicts": 0,
        "missing_year_for_movie": 0,
        "no_exact_vod_match": 0,
    }
    updated = []

    for channel in channels:
        if not isinstance(channel, dict) or str(channel.get("logo_url") or "").strip():
            continue
        name = str(channel.get("name") or "").strip()
        if not name:
            continue
        counts["channels_without_logo"] += 1
        base_title = channel_base_title(name)
        key = normalize_title(base_title)
        matches = lookup.get(key, [])
        if not matches:
            counts["no_exact_vod_match"] += 1
            continue
        counts["exact_title_matches"] += 1

        channel_year = extract_year(name)
        if channel_year:
            matches = [item for item in matches if item["year"] == channel_year]
            if not matches:
                counts["year_conflicts"] += 1
                continue

        # Series and anime indexes can intentionally expose the same canonical
        # VOD record. Collapse only identical IDs/years/posters, never remakes.
        unique = {
            (item["id"], item["year"], item["poster_url"]): item
            for item in matches
        }
        if len(unique) != 1:
            counts["ambiguous_vod_matches"] += 1
            continue
        match = next(iter(unique.values()))
        if match["section"] == "movies" and not channel_year and not match["year"]:
            counts["missing_year_for_movie"] += 1
            continue
        if not match["id"] or not match["poster_url"]:
            continue

        channel["logo_url"] = match["poster_url"]
        counts["artwork_applied"] += 1
        if len(updated) < 150:
            updated.append({
                "channel_id": str(channel.get("id") or ""),
                "channel_name": name,
                "vod_id": match["id"],
                "vod_title": match["title"],
                "year": match["year"],
                "poster_url": match["poster_url"],
            })

    if counts["artwork_applied"]:
        channel_doc["generated_at"] = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        atomic_write_json(channels_path, channel_doc)

    return {
        "schema_version": 1,
        "report_type": "channel_vod_poster_artwork_application",
        "catalog_mutated": bool(counts["artwork_applied"]),
        "counts": counts,
        "updated_channels": updated,
        "safety": [
            "Only channels with an empty logo_url are eligible.",
            "Only exact normalized VOD titles are considered after removing explicit 24H, season, and quality labels.",
            "A channel year must match the VOD year; year conflicts are rejected.",
            "Multiple distinct VOD records, remakes, and ambiguous matches are never assigned.",
            "Only TMDB poster artwork is used; channel names, streams, EPG IDs, and all playback fields are preserved.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/channel-vod-artwork-application.json"))
    args = parser.parse_args()
    report = build_report(args.root)
    output = args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "catalog_mutated": report["catalog_mutated"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
