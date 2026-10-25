#!/usr/bin/env python3
"""Read-only inventory and integrity audit for the CineHUB ACERVO repository.

This script never edits catalog files and never contacts external URLs. It reports
local counts and structural risks so an operator can review data before any merge.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VOD_CATEGORIES = ("movies", "series", "anime", "doramas")


def read_json(root: Path, relative: str, findings: list[dict[str, str]]) -> Any:
    path = root / relative
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        findings.append({"severity": "error", "code": "missing_file", "path": relative})
    except (OSError, json.JSONDecodeError) as exc:
        findings.append({"severity": "error", "code": "invalid_json", "path": relative,
                         "detail": str(exc)[:200]})
    return None


def audit(root: Path = ROOT) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    catalog_files = {
        "channels": "catalog/channels/channels.json",
        "radios": "catalog/radios/radios.json",
        "vod_manifest": "catalog/vod/index.json",
        "channel_sources": "sources/sources.json",
        "epg_sources": "catalog/epg/sources.json",
        "epg_map": "catalog/epg/channel-map.json",
        "epg_health": "catalog/epg/health.json",
        "xmltv_index": "catalog/epg/xmltv-channels.json",
    }
    loaded = {key: read_json(root, path, findings) for key, path in catalog_files.items()}

    def records(key: str, field: str) -> list[dict[str, Any]]:
        data = loaded.get(key)
        value = data.get(field, []) if isinstance(data, dict) else []
        if not isinstance(value, list):
            findings.append({"severity": "error", "code": "wrong_shape",
                             "path": catalog_files[key], "detail": field + " must be a list"})
            return []
        return [x for x in value if isinstance(x, dict)]

    channels = records("channels", "channels")
    radios = records("radios", "radios")
    counts["channels"] = len(channels)
    counts["radios"] = len(radios)
    for label, items in (("channels", channels), ("radios", radios)):
        ids = [str(x.get("id", "")).strip() for x in items]
        missing = sum(not ident for ident in ids)
        duplicates = [ident for ident, n in Counter(x for x in ids if x).items() if n > 1]
        if missing:
            findings.append({"severity": "warning", "code": "missing_ids", "path": label,
                             "detail": str(missing)})
        if duplicates:
            findings.append({"severity": "warning", "code": "duplicate_ids", "path": label,
                             "detail": ", ".join(sorted(duplicates)[:20])})

    manifest = loaded.get("vod_manifest")
    category_stats: dict[str, dict[str, int]] = {}
    if isinstance(manifest, dict):
        category_info = manifest.get("categories", {})
        for category in VOD_CATEGORIES:
            info = category_info.get(category, {}) if isinstance(category_info, dict) else {}
            index_path = info.get("index_path") if isinstance(info, dict) else None
            if index_path:
                index = read_json(root, index_path, findings)
                if not isinstance(index, list):
                    findings.append({"severity": "error", "code": "index_not_list",
                                     "path": str(index_path)})
                    index = []
            else:
                index = manifest.get(category, [])
                if not isinstance(index, list):
                    index = []
                    findings.append({"severity": "error", "code": "index_not_list",
                                     "path": "catalog/vod/index.json", "detail": category})
            ids = [str(item.get("id", "")).strip() for item in index if isinstance(item, dict)]
            duplicate_ids = [ident for ident, n in Counter(x for x in ids if x).items() if n > 1]
            missing_ids = sum(not ident for ident in ids)
            counts[category] = len(index)
            category_stats[category] = {
                "count": len(index), "manifest_count": int(info.get("count", len(index)))
                if isinstance(info, dict) else len(index),
                "missing_ids": missing_ids, "duplicate_ids": len(duplicate_ids),
            }
            if isinstance(info, dict) and "count" in info and info["count"] != len(index):
                findings.append({"severity": "error", "code": "manifest_count_mismatch",
                                 "path": str(index_path), "detail": f'{info["count"]} != {len(index)}'})
            if missing_ids:
                findings.append({"severity": "warning", "code": "missing_vod_ids",
                                 "path": str(index_path or category), "detail": str(missing_ids)})
            if duplicate_ids:
                findings.append({"severity": "warning", "code": "duplicate_vod_ids",
                                 "path": str(index_path or category),
                                 "detail": ", ".join(sorted(duplicate_ids)[:20])})

            # Verify detail references without loading or rewriting the full detail corpus.
            for item in index:
                if not isinstance(item, dict):
                    findings.append({"severity": "warning", "code": "non_object_vod_record",
                                     "path": str(index_path or category)})
                    continue
                detail_path = item.get("detail_path")
                if detail_path and not (root / str(detail_path)).is_file():
                    findings.append({"severity": "error", "code": "missing_detail",
                                     "path": str(detail_path), "detail": str(item.get("id", ""))})

    channel_sources = loaded.get("channel_sources")
    source_list = channel_sources.get("sources", []) if isinstance(channel_sources, dict) else []
    counts["registered_channel_sources"] = len(source_list) if isinstance(source_list, list) else 0
    epg_sources = loaded.get("epg_sources")
    epg_list = epg_sources.get("sources", []) if isinstance(epg_sources, dict) else []
    counts["registered_epg_sources"] = len(epg_list) if isinstance(epg_list, list) else 0
    epg_map = loaded.get("epg_map")
    counts["meuguia_mappings"] = len(epg_map.get("meuguia_codes", {})) if isinstance(epg_map, dict) and isinstance(epg_map.get("meuguia_codes"), dict) else 0
    counts["guiadetv_mappings"] = len(epg_map.get("guiadetv_slugs", {})) if isinstance(epg_map, dict) and isinstance(epg_map.get("guiadetv_slugs"), dict) else 0
    counts["xmltv_alias_keys"] = len(epg_map.get("xmltv_aliases", {})) if isinstance(epg_map, dict) and isinstance(epg_map.get("xmltv_aliases"), dict) else 0

    health = loaded.get("epg_health")
    health_sources = health.get("sources", {}) if isinstance(health, dict) else {}
    if isinstance(health_sources, dict):
        counts["epg_sources_healthy"] = sum(1 for x in health_sources.values()
                                            if isinstance(x, dict) and x.get("status") == "healthy")
        counts["epg_sources_unavailable"] = sum(1 for x in health_sources.values()
                                                if isinstance(x, dict) and x.get("status") == "unavailable")
    else:
        counts["epg_sources_healthy"] = 0
        counts["epg_sources_unavailable"] = 0

    xmltv = loaded.get("xmltv_index")
    xmltv_sources = xmltv.get("sources", {}) if isinstance(xmltv, dict) else {}
    counts["xmltv_index_sources"] = len(xmltv_sources) if isinstance(xmltv_sources, dict) else 0
    counts["xmltv_channels_indexed"] = sum(
        len(source.get("channels", [])) for source in xmltv_sources.values()
        if isinstance(source, dict) and isinstance(source.get("channels"), list)
    ) if isinstance(xmltv_sources, dict) else 0

    total_vod = sum(counts.get(x, 0) for x in VOD_CATEGORIES)
    counts["vod_total"] = total_vod
    return {
        "audit_schema_version": 1,
        "mode": "read-only",
        "repository": "CineHUB-ACERVO",
        "counts": counts,
        "vod_categories": category_stats,
        "findings_summary": dict(Counter(x["severity"] for x in findings)),
        "findings": findings,
        "preservation_note": "No catalog files were modified by this audit.",
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(x["severity"] == "error" for x in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
