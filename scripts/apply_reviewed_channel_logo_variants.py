#!/usr/bin/env python3
"""Apply explicitly reviewed quality-variant channel logos without overwrites."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .suggest_channel_logo_matches import CHANNELS_FILE, ROOT, build_report, norm_without_quality
except ImportError:
    from suggest_channel_logo_matches import CHANNELS_FILE, ROOT, build_report, norm_without_quality

MANIFEST_FILE = "catalog/reference/reviewed-channel-logo-variants.json"


def apply(root: Path = ROOT) -> dict[str, Any]:
    channels_path = root / CHANNELS_FILE
    manifest_path = root / MANIFEST_FILE
    document = json.loads(channels_path.read_text(encoding="utf-8"))
    channels = document.get("channels", []) if isinstance(document, dict) else []
    if not isinstance(channels, list):
        raise ValueError("catalog/channels/channels.json must contain a channels array")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    variants = manifest.get("reviewed_variants", []) if isinstance(manifest, dict) else []
    approved: dict[str, str] = {}
    for item in variants:
        if not isinstance(item, dict):
            continue
        channel_id = str(item.get("channel_id") or "").strip()
        reference_name = str(item.get("reference_name") or "").strip()
        if channel_id and reference_name:
            if channel_id in approved:
                raise ValueError(f"Duplicate reviewed channel ID: {channel_id}")
            approved[channel_id] = reference_name

    report = build_report(root)
    suggestions = {
        str(item.get("channel_id") or ""): item
        for item in report.get("suggestions", [])
        if isinstance(item, dict)
    }
    by_id: dict[str, list[dict[str, Any]]] = {}
    for channel in channels:
        if isinstance(channel, dict) and channel.get("id"):
            by_id.setdefault(str(channel["id"]), []).append(channel)

    applied: list[dict[str, str]] = []
    skipped_existing = skipped_unapproved = skipped_mismatch = skipped_invalid = 0
    for channel_id, reference_name in approved.items():
        matches = by_id.get(channel_id, [])
        suggestion = suggestions.get(channel_id)
        if len(matches) != 1:
            skipped_invalid += 1
            continue
        channel = matches[0]
        if str(channel.get("logo_url") or "").strip():
            skipped_existing += 1
            continue
        if not suggestion:
            skipped_invalid += 1
            continue
        if suggestion.get("status") != "quality_marker_normalized_review":
            skipped_unapproved += 1
            continue
        if str(suggestion.get("reference_name") or "") != reference_name:
            skipped_mismatch += 1
            continue
        if norm_without_quality(channel.get("name")) != norm_without_quality(reference_name):
            skipped_mismatch += 1
            continue
        logo_url = str(suggestion.get("suggested_logo_url") or "").strip()
        if not logo_url.startswith("https://"):
            skipped_invalid += 1
            continue
        channel["logo_url"] = logo_url
        applied.append({
            "channel_id": channel_id,
            "channel_name": str(channel.get("name") or ""),
            "reference_name": reference_name,
            "logo_url": logo_url,
        })

    if applied:
        channels_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "report_type": "reviewed_channel_logo_variant_application",
        "catalog_mutated": bool(applied),
        "reviewed_variants": len(approved),
        "applied": len(applied),
        "skipped_existing": skipped_existing,
        "skipped_unapproved": skipped_unapproved,
        "skipped_mismatch": skipped_mismatch,
        "skipped_invalid": skipped_invalid,
        "updated_channels": applied,
        "safety": [
            "Only explicit channel IDs in the reviewed allowlist are eligible.",
            "Only one unique HTTPS reference-logo suggestion is accepted per channel.",
            "Channel and reference names must match after removing only quality markers and normalizing punctuation/case.",
            "Existing logo_url values and all stream, EPG, group, and playback fields are preserved.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = apply(args.root)
    print(json.dumps({key: value for key, value in result.items() if key != "updated_channels"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
