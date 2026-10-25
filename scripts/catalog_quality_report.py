#!/usr/bin/env python3
"""Build a read-only, actionable quality report without exposing source URLs."""
from __future__ import annotations
import json, re, unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VOD_SECTIONS = ("movies", "series", "anime", "doramas")
MAX_FINDINGS_PER_RULE = 500
MAX_DUPLICATE_GROUPS = 250

def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)

def normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()

def add_missing(target, totals, rule, record_id, title, category=""):
    totals[rule] = totals.get(rule, 0) + 1
    bucket = target.setdefault(rule, [])
    if len(bucket) < MAX_FINDINGS_PER_RULE:
        item = {"id": str(record_id or "?"), "title": str(title or "")[:180]}
        if category:
            item["category"] = category
        bucket.append(item)

def build_report(root: Path = ROOT) -> dict[str, Any]:
    """Summarize metadata gaps and duplicate-title candidates; never mutate input."""
    missing = {}
    missing_totals = {}
    counts = {}
    duplicate_titles = defaultdict(list)
    channels_doc = load_json(root / "catalog/channels/channels.json")
    channels = channels_doc.get("channels", []) if isinstance(channels_doc, dict) else []
    counts["channels"] = len(channels) if isinstance(channels, list) else 0
    for record in channels if isinstance(channels, list) else []:
        if not isinstance(record, dict): continue
        ident, title = record.get("id"), record.get("name")
        if not record.get("logo_url"): add_missing(missing, missing_totals, "channels_missing_logo", ident, title)
        if not record.get("group"): add_missing(missing, "channels_missing_group", ident, title)
        if not record.get("epg_id"): add_missing(missing, "channels_missing_epg_id", ident, title)
        if not isinstance(record.get("sources"), list) or not record.get("sources"):
            add_missing(missing, "channels_without_source_list", ident, title)
    radios_doc = load_json(root / "catalog/radios/radios.json")
    radios = radios_doc.get("radios", []) if isinstance(radios_doc, dict) else []
    counts["radios"] = len(radios) if isinstance(radios, list) else 0
    for record in radios if isinstance(radios, list) else []:
        if not isinstance(record, dict): continue
        ident, title = record.get("id"), record.get("name")
        if not record.get("logo_url"): add_missing(missing, "radios_missing_logo", ident, title)
        if not record.get("genre"): add_missing(missing, "radios_missing_genre", ident, title)
        if not record.get("stream_url"): add_missing(missing, "radios_missing_stream", ident, title)
    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {}) if isinstance(manifest, dict) else {}
    vod_total = 0
    for section in VOD_SECTIONS:
        info = categories.get(section, {}) if isinstance(categories, dict) else {}
        index_path = info.get("index_path", f"catalog/vod/index/{section}.json")
        records = load_json(root / index_path)
        if not isinstance(records, list): records = []
        counts[f"vod_{section}"] = len(records)
        vod_total += len(records)
        for record in records:
            if not isinstance(record, dict): continue
            ident, title = record.get("id"), record.get("title")
            if not record.get("poster_url"): add_missing(missing, "vod_missing_poster", ident, title, section)
            if not record.get("year"): add_missing(missing, "vod_missing_year", ident, title, section)
            if not isinstance(record.get("genres"), list) or not record.get("genres"):
                add_missing(missing, "vod_missing_genres", ident, title, section)
            if not record.get("detail_path"): add_missing(missing, "vod_missing_detail_path", ident, title, section)
            normalized = normalize_title(title)
            if normalized:
                duplicate_titles[normalized].append({"id": str(ident or "?"), "title": str(title or "")[:180], "category": section})
    dupes = []
    total_dupe_groups = 0
    for normalized, items in sorted(duplicate_titles.items()):
        if len(items) < 2: continue
        total_dupe_groups += 1
        if len(dupes) < MAX_DUPLICATE_GROUPS:
            dupes.append({"normalized_title": normalized, "items": items[:10], "count": len(items)})
    return {
        "report_version": 1, "mode": "read_only_structural_review",
        "privacy": "No stream, logo, or source URLs are included.",
        "counts": {**counts, "vod_total": vod_total},
        "missing_metadata": {rule: {"count": missing_totals.get(rule, len(items)), "items_included": len(items), "truncated": missing_totals.get(rule, len(items)) > len(items), "items": items} for rule, items in sorted(missing.items())},
        "duplicate_title_candidates": {"count_included": len(dupes), "truncated": total_dupe_groups > len(dupes), "groups": dupes,
            "warning": "Candidates require review; normalized title equality does not prove duplicate content."},
        "limitations": [
            "Field presence does not prove a stream or image URL works.",
            "Missing metadata is not automatically filled or inferred.",
            "No catalog files are changed and no network requests are made.",
            "Finding lists are capped; per-rule counts reflect emitted items and indicate truncation.",
        ],
    }

def main():
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
