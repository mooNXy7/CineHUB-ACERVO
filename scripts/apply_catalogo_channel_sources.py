#!/usr/bin/env python3
"""Apply only exact-match, network-confirmed HLS sources to empty channels."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .suggest_catalogo_channel_sources import safe_reference_stream
    from .update_catalog import atomic_write_json
except ImportError:
    from suggest_catalogo_channel_sources import safe_reference_stream
    from update_catalog import atomic_write_json

ROOT = Path(__file__).resolve().parents[1]


def apply_verified_sources(channels_path: Path, candidates_path: Path,
                           health_path: Path, report_path: Path) -> dict:
    catalog = json.loads(channels_path.read_text(encoding="utf-8"))
    candidate_report = json.loads(candidates_path.read_text(encoding="utf-8"))
    health_report = json.loads(health_path.read_text(encoding="utf-8"))
    health_by_key = {
        (str(item.get("channel_id")), int(item.get("source_order") or 0)): item
        for item in health_report.get("results", [])
    }
    channels = catalog.get("channels", [])
    by_id = {str(item.get("id")): item for item in channels if isinstance(item, dict) and item.get("id")}
    counts = {
        "candidate_channels": len(candidate_report.get("candidates", [])),
        "channels_updated": 0, "hls_sources_added": 0,
        "skipped_channel_missing": 0, "skipped_channel_has_source": 0,
        "skipped_no_healthy_hls": 0, "skipped_unsafe": 0,
    }
    updated_ids = []
    for candidate in candidate_report.get("candidates", []):
        channel_id = str(candidate.get("channel_id") or "")
        target = by_id.get(channel_id)
        if target is None:
            counts["skipped_channel_missing"] += 1
            continue
        if target.get("sources"):
            counts["skipped_channel_has_source"] += 1
            continue
        additions = []
        for source in candidate.get("sources", []):
            key = (channel_id, int(source.get("source_order") or 0))
            health = health_by_key.get(key) or {}
            if health.get("probe_status") != "hls_ok" or source.get("source_type") != "hls":
                continue
            url = str(source.get("url") or "")
            safe, _ = safe_reference_stream(url)
            if not safe:
                counts["skipped_unsafe"] += 1
                continue
            parsed = urlsplit(url)
            entry = {
                "url": url,
                "priority": 30 + int(source.get("source_order") or 1),
                "source_id": "saimoplayer-catalogo",
            }
            headers = source.get("headers") if isinstance(source.get("headers"), dict) else {}
            agent = str(headers.get("user_agent") or "").strip()
            referer = str(headers.get("referer") or "").strip()
            if agent and len(agent) <= 512 and not any(ch in agent for ch in "\r\n"):
                entry["user_agent"] = agent
                entry["userAgent"] = agent
            if referer:
                ref_ok, _ = safe_reference_stream(referer)
                if ref_ok:
                    entry["referer"] = referer
            additions.append(entry)
        if not additions:
            counts["skipped_no_healthy_hls"] += 1
            continue
        # Recheck immediately before mutation: never replace an existing source.
        if target.get("sources"):
            counts["skipped_channel_has_source"] += 1
            continue
        target["sources"] = additions
        counts["channels_updated"] += 1
        counts["hls_sources_added"] += len(additions)
        if len(updated_ids) < 200:
            updated_ids.append(channel_id)

    changed = counts["channels_updated"] > 0
    if changed:
        catalog["generated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(channels_path, catalog)
    report = {
        "schema_version": 1,
        "report_type": "applied_network_confirmed_catalogo_hls_sources",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_mutated": changed,
        "counts": counts,
        "updated_channel_ids": updated_ids,
        "safety": [
            "Only exact-name channel candidates from the authorized catalogo.txt report are considered.",
            "Only HTTPS sources that returned an HLS #EXTM3U playlist are applied.",
            "Only channels with an empty sources array are updated; existing sources and metadata are never overwritten.",
            "Only safe User-Agent and HTTPS Referer are copied; no authorization, cookie, or DRM data is imported.",
            "A successful playlist probe is not a physical TV playback test; stream_status is not marked healthy.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels", type=Path, default=ROOT / "catalog/channels/channels.json")
    parser.add_argument("--candidates", type=Path, default=ROOT / "reports/catalogo-channel-source-candidates.json")
    parser.add_argument("--health", type=Path, default=ROOT / "reports/catalogo-channel-source-health.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/catalogo-channel-source-application.json")
    args = parser.parse_args()
    report = apply_verified_sources(args.channels, args.candidates, args.health, args.output)
    print(json.dumps({"counts": report["counts"], "catalog_mutated": report["catalog_mutated"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
