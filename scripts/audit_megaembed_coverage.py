#!/usr/bin/env python3
"""Read-only coverage audit for MegaEmbed fallback references in VOD details."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOSTS = {"mgeb.top", "www.mgeb.top", "megaembedapi.site"}
IMDB = re.compile(r"^tt\d{7,10}$")


def load_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def source_is_megaembed(source: dict) -> bool:
    url = str(source.get("url") or "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in ALLOWED_HOSTS and parsed.path.startswith("/embed/")


def iter_seasons(record: dict):
    """Support legacy list seasons and the importer’s canonical keyed object."""
    seasons = record.get("seasons")
    if isinstance(seasons, dict):
        yield from seasons.values()
    elif isinstance(seasons, list):
        yield from seasons


def iter_episodes(record: dict):
    for season in iter_seasons(record):
        if not isinstance(season, dict):
            continue
        episodes = season.get("episodes", [])
        if not isinstance(episodes, list):
            continue
        for episode in episodes:
            if isinstance(episode, dict):
                yield episode


def iter_source_lists(record: dict):
    sources = record.get("sources")
    if isinstance(sources, list):
        yield sources
    for episode in iter_episodes(record):
        sources = episode.get("sources")
        if isinstance(sources, list):
            yield sources


def audit(root: Path) -> dict:
    manifest = load_json(root / "catalog/vod/index.json")
    result = {
        "schema_version": 1,
        "read_only": True,
        "categories": {},
        "totals": {
            "records": 0,
            "records_with_tmdb_id": 0,
            "records_with_imdb_id": 0,
            "records_with_any_provider_id": 0,
            "records_with_megaembed": 0,
            "megaembed_source_urls": 0,
            "episodes": 0,
            "episodes_with_megaembed": 0,
            "invalid_megaembed_urls": 0
        }
    }
    detail_cache: dict[str, list] = {}
    seen_records: set[tuple[str, str]] = set()

    for category, config in manifest.get("categories", {}).items():
        index_path = root / config["index_path"]
        entries = load_json(index_path)
        counts = {
            "records": 0, "with_tmdb_id": 0, "with_imdb_id": 0,
            "with_any_provider_id": 0, "with_megaembed": 0,
            "megaembed_source_urls": 0, "episodes": 0,
            "episodes_with_megaembed": 0
        }
        detail_paths = sorted({str(entry.get("detail_path") or "") for entry in entries if entry.get("detail_path")})
        for relative in detail_paths:
            if relative not in detail_cache:
                detail_cache[relative] = load_json(root / relative)
            records = detail_cache[relative]
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                ident = str(record.get("id") or "")
                key = (category, ident)
                if key in seen_records:
                    continue
                seen_records.add(key)
                counts["records"] += 1
                tmdb = str(record.get("tmdb_id") or "").strip()
                imdb = str(record.get("imdb_id") or "").strip()
                if tmdb.isdigit():
                    counts["with_tmdb_id"] += 1
                if IMDB.fullmatch(imdb):
                    counts["with_imdb_id"] += 1
                if tmdb.isdigit() or IMDB.fullmatch(imdb):
                    counts["with_any_provider_id"] += 1

                record_has_embed = False
                for source_list in iter_source_lists(record):
                    for source in source_list:
                        if not isinstance(source, dict):
                            continue
                        url = str(source.get("url") or "").strip()
                        try:
                            host = (urlsplit(url).hostname or "").lower() if url else ""
                        except ValueError:
                            host = ""
                        if host in ALLOWED_HOSTS:
                            if source_is_megaembed(source):
                                counts["megaembed_source_urls"] += 1
                                record_has_embed = True
                            else:
                                result["totals"]["invalid_megaembed_urls"] += 1
                if record_has_embed:
                    counts["with_megaembed"] += 1

                for episode in iter_episodes(record):
                    counts["episodes"] += 1
                    episode_sources = episode.get("sources", [])
                    if isinstance(episode_sources, list) and any(
                        source_is_megaembed(source)
                        for source in episode_sources
                        if isinstance(source, dict)
                    ):
                        counts["episodes_with_megaembed"] += 1

        result["categories"][category] = counts
        for key in result["totals"]:
            if key in counts:
                result["totals"][key] += counts[key]

    result["totals"]["records_with_tmdb_id"] = sum(x["with_tmdb_id"] for x in result["categories"].values())
    result["totals"]["records_with_imdb_id"] = sum(x["with_imdb_id"] for x in result["categories"].values())
    result["totals"]["records_with_any_provider_id"] = sum(x["with_any_provider_id"] for x in result["categories"].values())
    result["totals"]["records_with_megaembed"] = sum(x["with_megaembed"] for x in result["categories"].values())
    result["totals"]["megaembed_source_urls"] = sum(x["megaembed_source_urls"] for x in result["categories"].values())
    result["totals"]["episodes"] = sum(x["episodes"] for x in result["categories"].values())
    result["totals"]["episodes_with_megaembed"] = sum(x["episodes_with_megaembed"] for x in result["categories"].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
