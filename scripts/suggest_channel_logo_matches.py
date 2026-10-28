#!/usr/bin/env python3
"""Build read-only channel-logo suggestions from the sanitized Saimo reference.

Only blank catalog logo fields are considered. Matching is exact after Unicode,
accent, case, and common broadcast-quality-marker normalization. No stream,
DRM, headers, or playback data is read or imported, and the catalog is never
modified.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = "catalog/channels/channels.json"
REFERENCE_FILE = "catalog/reference/saimo-channel-logos.json"


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\\b(?:hd|sd|fhd|uhd|4k|br)\\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(root: Path = ROOT) -> dict[str, Any]:
    channels_doc = load_json(root / CHANNELS_FILE)
    reference_doc = load_json(root / REFERENCE_FILE)
    channels = channels_doc.get("channels", [])
    entries = reference_doc.get("entries", [])

    by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in entries:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        logo = str(item.get("logo_url") or "").strip()
        if name and logo.startswith("https://"):
            by_name[norm(name)].append({"name": name, "logo_url": logo})

    suggestions = []
    already_has_logo = 0
    missing_logo = 0
    no_reference = 0
    ambiguous = 0
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        name = str(channel.get("name") or "").strip()
        if not name:
            continue
        current_logo = str(channel.get("logo_url") or "").strip()
        if current_logo:
            already_has_logo += 1
            continue
        missing_logo += 1
        matches = by_name.get(norm(name), [])
        unique_logos = {item["logo_url"] for item in matches}
        if len(unique_logos) == 1:
            match = matches[0]
            suggestions.append({
                "channel_id": str(channel.get("id") or ""),
                "channel_name": name,
                "suggested_logo_url": match["logo_url"],
                "reference_name": match["name"],
                "status": "exact_normalized_name_review",
                "automatic_update": False,
            })
        elif len(unique_logos) > 1:
            ambiguous += 1
        else:
            no_reference += 1

    return {
        "schema_version": 1,
        "report_type": "review_only_channel_logo_suggestions",
        "read_only": True,
        "catalog_mutated": False,
        "source": reference_doc.get("source", ""),
        "source_fields_used": ["name", "logo_url"],
        "stream_or_drm_data_imported": False,
        "fuzzy_matching_used": False,
        "counts": {
            "catalog_channels": len(channels),
            "channels_with_logo": already_has_logo,
            "channels_missing_logo_examined": missing_logo,
            "candidate_channels": len(suggestions),
            "ambiguous_reference_matches": ambiguous,
            "no_reference_match": no_reference,
        },
        "suggestions": suggestions,
        "notes": [
            "Suggestions only; no channel record or logo is changed automatically.",
            "Only HTTPS logo references are included; streams, DRM keys, headers, and playback fields are excluded.",
            "Exact normalized names can still refer to regional variants; review before applying.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/channel-logo-suggestions.json"))
    args = parser.parse_args()
    report = build_report(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "counts": report["counts"],
                      "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
