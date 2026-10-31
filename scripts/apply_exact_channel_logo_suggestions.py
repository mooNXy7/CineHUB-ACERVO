#!/usr/bin/env python3
"""Apply only exact, unambiguous channel-logo matches; preserve all other fields."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .suggest_channel_logo_matches import CHANNELS_FILE, ROOT, build_report, norm
except ImportError:  # Executed as a standalone script from the scripts directory.
    from suggest_channel_logo_matches import CHANNELS_FILE, ROOT, build_report, norm


def apply(root: Path = ROOT) -> dict[str, Any]:
    channels_path = root / CHANNELS_FILE
    document = json.loads(channels_path.read_text(encoding="utf-8"))
    channels = document.get("channels", []) if isinstance(document, dict) else []
    if not isinstance(channels, list):
        raise ValueError("catalog/channels/channels.json must contain a channels array")

    report = build_report(root)
    by_id: dict[str, list[dict[str, Any]]] = {}
    for channel in channels:
        if isinstance(channel, dict) and channel.get("id"):
            by_id.setdefault(str(channel["id"]), []).append(channel)

    applied: list[dict[str, str]] = []
    skipped_lower_confidence = 0
    skipped_existing = 0
    skipped_invalid = 0
    for suggestion in report.get("suggestions", []):
        if suggestion.get("status") != "exact_normalized_name_review" or suggestion.get("confidence") != "higher":
            skipped_lower_confidence += 1
            continue
        channel_id = str(suggestion.get("channel_id") or "")
        matches = by_id.get(channel_id, [])
        if len(matches) != 1:
            skipped_invalid += 1
            continue
        channel = matches[0]
        if str(channel.get("logo_url") or "").strip():
            skipped_existing += 1
            continue
        logo_url = str(suggestion.get("suggested_logo_url") or "").strip()
        if not logo_url.startswith("https://") or norm(channel.get("name")) != norm(suggestion.get("reference_name")):
            skipped_invalid += 1
            continue
        channel["logo_url"] = logo_url
        applied.append({"channel_id": channel_id, "channel_name": str(channel.get("name") or ""), "logo_url": logo_url})

    if applied:
        channels_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "report_type": "exact_channel_logo_application",
        "catalog_mutated": bool(applied),
        "applied": len(applied),
        "skipped_lower_confidence": skipped_lower_confidence,
        "skipped_existing": skipped_existing,
        "skipped_invalid": skipped_invalid,
        "updated_channels": applied,
        "safety": [
            "Only exact normalized-name matches with one HTTPS logo candidate were applied.",
            "Existing logo_url values were never overwritten.",
            "Lower-confidence quality-marker matches were not applied.",
            "Stream URLs, EPG IDs, groups, headers, DRM and all other fields were preserved.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = apply(args.root)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
