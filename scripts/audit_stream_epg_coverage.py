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

    meuguia = {norm(k) for k in (epg_map.get("meuguia_codes") or {})}
    guide = {norm(k) for k in (epg_map.get("guiadetv_slugs") or {})}
    aliases = epg_map.get("xmltv_aliases") or {}
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
            or any(name_key in names or bool(names & xmltv_names) for names in alias_names.values())
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
        "audit_schema_version": 1,
        "mode": "read-only",
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
