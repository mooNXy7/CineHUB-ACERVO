#!/usr/bin/env python3
"""Fill only missing CineHUB channel streams from authorized, non-DRM SaimoTV references."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any

try:
    from .update_catalog import ROOT, atomic_write_json, normalize_key, safe_https_url
except ImportError:
    from update_catalog import ROOT, atomic_write_json, normalize_key, safe_https_url

CHANNELS_FILE = ROOT / "catalog/channels/channels.json"
CREDENTIAL_PATH = re.compile(r"/(?:live|movie|series)/[^/]{3,}/[^/]{3,}/", re.I)
QUALITY = re.compile(r"\b(4k|uhd|fhd|hd|sd|1080p|720p)\b", re.I)
SENSITIVE_PATH = re.compile(r"(?:token|auth|password|passwd|username|signature|session|expires)", re.I)


def normalize_channel_name(value: Any) -> str:
    value = normalize_key(value)
    value = QUALITY.sub(" ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def source_is_safe(stream: dict[str, Any], channel: dict[str, Any]) -> bool:
    drm = channel.get("drm_system") if isinstance(channel.get("drm_system"), dict) else {}
    if str(drm.get("clearKey") or "").strip() or str(drm.get("widevine") or "").strip():
        return False
    url = str(stream.get("url") or "").strip()
    if not safe_https_url(url) or not re.search(r"\.m3u8(?:[?#]|$)", url, re.I):
        return False
    path = url.split("?", 1)[0].split("#", 1)[0]
    if CREDENTIAL_PATH.search(path) or SENSITIVE_PATH.search(path):
        return False
    if re.search(r"(?:coming|placeholder)\.(?:mp4|m3u8)$", path, re.I):
        return False
    return True


def choose_channel(candidates: list[dict[str, Any]], quality: str) -> dict[str, Any] | None:
    if len(candidates) == 1:
        return candidates[0]
    marker = str(quality or "").strip().casefold()
    if marker:
        matching = [
            item for item in candidates
            if re.search(rf"\b{re.escape(marker)}\b", str(item.get("name") or ""), re.I)
        ]
        if len(matching) == 1:
            return matching[0]
    return None


def update(root: Path = ROOT, reference_file: Path | None = None) -> dict[str, Any]:
    reference_file = reference_file or Path("/tmp/cinehub-saimo-tv/scripts/offline.json")
    channels_path = root / "catalog/channels/channels.json"
    current = json.loads(channels_path.read_text(encoding="utf-8"))
    if not isinstance(current, dict) or not isinstance(current.get("channels"), list):
        raise ValueError("catalog/channels/channels.json must contain a channels array")
    reference = json.loads(reference_file.read_text(encoding="utf-8"))
    records = reference.get("data", []) if isinstance(reference, dict) else []
    if not isinstance(records, list):
        raise ValueError("SaimoTV offline reference must contain a data array")

    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in current["channels"]:
        if isinstance(item, dict) and item.get("name"):
            by_name.setdefault(normalize_channel_name(item["name"]), []).append(item)

    counts = {
        "reference_channels": len(records),
        "safe_hls_candidates": 0,
        "matched_unique_channels": 0,
        "streams_added": 0,
        "skipped_drm": 0,
        "skipped_unsafe": 0,
        "already_has_stream": 0,
        "unmatched": 0,
        "ambiguous": 0,
        "updated_channel_ids": [],
    }
    for record in records:
        if not isinstance(record, dict) or not str(record.get("name") or "").strip():
            continue
        key = normalize_channel_name(record["name"])
        candidates = by_name.get(key, [])
        if not candidates:
            counts["unmatched"] += 1
            continue
        streams = record.get("streams") if isinstance(record.get("streams"), list) else []
        for stream in streams:
            if not isinstance(stream, dict):
                continue
            drm = record.get("drm_system") if isinstance(record.get("drm_system"), dict) else {}
            if str(drm.get("clearKey") or "").strip() or str(drm.get("widevine") or "").strip():
                counts["skipped_drm"] += 1
                continue
            if not source_is_safe(stream, record):
                counts["skipped_unsafe"] += 1
                continue
            counts["safe_hls_candidates"] += 1
            target = choose_channel(candidates, str(stream.get("quality") or ""))
            if target is None:
                counts["ambiguous"] += 1
                continue
            counts["matched_unique_channels"] += 1
            existing = target.get("sources") if isinstance(target.get("sources"), list) else []
            if existing:
                counts["already_has_stream"] += 1
                continue
            target["sources"] = [{
                "url": str(stream["url"]).strip(),
                "priority": 30,
                "source_id": "saimotv-android-offline-reference",
            }]
            counts["streams_added"] += 1
            if len(counts["updated_channel_ids"]) < 100:
                counts["updated_channel_ids"].append(str(target.get("id") or target.get("name") or ""))

    changed = counts["streams_added"] > 0
    if changed:
        current["generated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(channels_path, current)
    report = {
        "schema_version": 1,
        "report_type": "authorized_saimotv_channel_stream_refresh",
        "catalog_mutated": changed,
        "counts": counts,
        "safety": [
            "Only exact normalized channel names are matched; quality variants must match the source quality.",
            "Only HTTPS HLS playlists without embedded credentials or sensitive tokens are eligible.",
            "Records with ClearKey or Widevine DRM are never imported.",
            "Existing channel streams and all existing channel metadata are preserved.",
            "Only stream URLs are imported; DRM keys and request headers are not copied.",
        ],
    }
    report_path = root / "reports/saimotv-channel-stream-refresh.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reference-file", type=Path, default=Path("/tmp/cinehub-saimo-tv/scripts/offline.json"))
    args = parser.parse_args()
    update(args.root, args.reference_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
