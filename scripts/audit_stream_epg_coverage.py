#!/usr/bin/env python3
"""Read-only coverage audit for channel streams and EPG associations.

No network requests are made and no catalog files are written. This measures
structural associations only; it does not claim that streams or schedules play.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\b(?:hd|sd|fhd|uhd|4k|br)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def load(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def audit_coverage(root: Path = ROOT) -> dict[str, Any]:
    channels_doc = load(root, "catalog/channels/channels.json")
    radios_doc = load(root, "catalog/radios/radios.json")
    epg_map = load(root, "catalog/epg/channel-map.json")
    xmltv_doc = load(root, "catalog/epg/xmltv-channels.json")
    channels = channels_doc.get("channels", [])
    radios = radios_doc.get("radios", [])

    meuguia_map = epg_map.get("meuguia_codes") or {}
    guide_map = epg_map.get("guiadetv_slugs") or {}
    meuguia = {norm(k) for k in meuguia_map}
    guide = {norm(k) for k in guide_map}
    aliases = epg_map.get("xmltv_aliases") or {}
    channel_names = {
        norm(item.get("name"))
        for item in channels
        if isinstance(item, dict) and item.get("name")
    }
    meuguia_stale = sorted(str(name) for name in meuguia_map if norm(name) not in channel_names)
    guide_stale = sorted(str(name) for name in guide_map if norm(name) not in channel_names)
    meuguia_code_groups: dict[str, list[str]] = {}
    for channel_name, code in meuguia_map.items():
        meuguia_code_groups.setdefault(str(code).strip(), []).append(str(channel_name))
    duplicate_meuguia_codes = [
        {"code": code, "channel_names": sorted(names)}
        for code, names in sorted(meuguia_code_groups.items())
        if code and len(names) > 1
    ]
    xmltv_names: set[str] = set()
    xmltv_ids: set[str] = set()
    xmltv_sources = xmltv_doc.get("sources") or {}
    for source in xmltv_sources.values():
        if not isinstance(source, dict):
            continue
        for item in source.get("channels", []):
            if not isinstance(item, dict):
                continue
            if item.get("id"):
                xmltv_ids.add(str(item["id"]).strip())
            for name in item.get("display_names", []):
                if name:
                    xmltv_names.add(norm(name))

    alias_names: dict[str, set[str]] = {}
    for key, values in aliases.items():
        alias_names[norm(key)] = {norm(key), *(norm(v) for v in values if v)}

    stats = Counter()
    examples: dict[str, list[str]] = {
        "no_stream": [], "no_epg_association": [], "epg_id_not_in_xmltv": []
    }
    for item in channels:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or "(unnamed)")
        sources = item.get("sources") or []
        usable_sources = [s for s in sources if isinstance(s, dict) and s.get("url")]
        stats["channels"] += 1
        stats["channels_with_stream_reference"] += bool(usable_sources)
        if not usable_sources and len(examples["no_stream"]) < 25:
            examples["no_stream"].append(name)

        epg_id = str(item.get("epg_id") or "").strip()
        name_key = norm(name)
        has_mapping = bool(
            (epg_id and epg_id in xmltv_ids)
            or name_key in meuguia
            or name_key in guide
            or name_key in xmltv_names
            or bool(alias_names.get(name_key, set()) & xmltv_names)
        )
        stats["channels_with_epg_association"] += has_mapping
        if epg_id and epg_id in xmltv_ids:
            stats["epg_ids_found_in_xmltv_index"] += 1
        elif epg_id:
            stats["epg_ids_not_found_in_xmltv_index"] += 1
            if len(examples["epg_id_not_in_xmltv"]) < 25:
                examples["epg_id_not_in_xmltv"].append(f"{name} ({epg_id})")
        if not has_mapping and len(examples["no_epg_association"]) < 25:
            examples["no_epg_association"].append(name)

    for item in radios:
        if not isinstance(item, dict):
            continue
        stats["radios"] += 1
        stats["radios_with_stream_reference"] += bool(item.get("stream_url"))

    total = stats["channels"]
    return {
        "audit_schema_version": 2,
        "mode": "read-only",
        "epg_map_review": {
            "meuguia_map_entries": len(meuguia_map),
            "guiadetv_map_entries": len(guide_map),
            "meuguia_entries_without_normalized_catalog_name": {
                "count": len(meuguia_stale), "examples": meuguia_stale[:50],
                "warning": "Candidate stale mappings only after accent/case/quality-marker normalization; aliases and regional naming differences may be intentional."
            },
            "guiadetv_entries_without_normalized_catalog_name": {
                "count": len(guide_stale), "examples": guide_stale[:50],
                "warning": "Candidate stale mappings only after accent/case/quality-marker normalization; aliases and regional naming differences may be intentional."
            },
            "duplicate_meuguia_codes": {
                "count": len(duplicate_meuguia_codes), "groups": duplicate_meuguia_codes[:50],
                "warning": "Shared external codes require manual review and are never changed automatically."
            }
        },
        "network_requests": 0,
        "catalog_files_modified": False,
        "counts": dict(stats),
        "coverage": {
            "channel_stream_reference_pct": round(100 * stats["channels_with_stream_reference"] / total, 2) if total else 0,
            "channel_epg_structural_association_pct": round(100 * stats["channels_with_epg_association"] / total, 2) if total else 0,
            "radio_stream_reference_pct": round(100 * stats["radios_with_stream_reference"] / stats["radios"], 2) if stats["radios"] else 0,
        },
        "examples_limited_to_25": examples,
        "limitations": [
            "A source reference is not proof that a stream is reachable or playable.",
            "An EPG association is structural only; it does not prove current programme coverage.",
            "XMLTV channel IDs are aggregated from the locally indexed feeds; aliases can create false positives and require review."
        ]
    }


def main() -> int:
    result = audit_coverage()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
