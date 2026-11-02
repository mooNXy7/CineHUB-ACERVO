#!/usr/bin/env python3
"""Generate review-only EPG mapping candidates from unique exact normalized names.

This tool never writes channel records. It deliberately avoids fuzzy matching,
regional substitutions, and automatic epg_id assignment.
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


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\b(?:hd|sd|fhd|uhd|4k|br)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def build_report(root: Path = ROOT) -> dict[str, Any]:
    channels_doc = load_json(root / "catalog/channels/channels.json")
    index_doc = load_json(root / "catalog/epg/xmltv-channels.json")
    map_doc = load_json(root / "catalog/epg/channel-map.json")
    channels = channels_doc.get("channels", [])
    indexed_sources = index_doc.get("sources", {})
    aliases = map_doc.get("xmltv_aliases", {})
    meuguia_names = {norm(name) for name in (map_doc.get("meuguia_codes") or {})}
    guiadetv_names = {norm(name) for name in (map_doc.get("guiadetv_slugs") or {})}
    html_mapped_names = meuguia_names | guiadetv_names

    # Build normalized display-name -> source-specific XMLTV IDs. Preserve
    # collisions as ambiguity instead of choosing whichever source came first.
    names_to_ids: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for source_id, source in indexed_sources.items():
        if not isinstance(source, dict):
            continue
        for item in source.get("channels", []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            for display_name in item.get("display_names", []):
                key = norm(display_name)
                if key:
                    names_to_ids[key][str(source_id)].add(str(item["id"]).strip())

    # Resolve aliases in both directions: canonical channel names may be
    # stored in the catalog while the XMLTV feed uses an alias, or vice versa.
    # Keep a normalized equivalence group but do not collapse source-specific IDs.
    alias_lookup: dict[str, set[str]] = defaultdict(set)
    for canonical, values in aliases.items():
        canonical_key = norm(canonical)
        if not canonical_key:
            continue
        alias_keys = {canonical_key}
        if isinstance(values, list):
            alias_keys.update(norm(value) for value in values if norm(value))
        for alias_key in alias_keys:
            alias_lookup[alias_key].update(alias_keys)

    candidates = []
    no_exact_match = []
    already_mapped = 0
    html_mapped = 0
    ambiguous = 0
    for channel in channels:
        if not isinstance(channel, dict):
            continue
        channel_name = str(channel.get("name") or "").strip()
        if not channel_name:
            continue
        current_id = str(channel.get("epg_id") or "").strip()
        current_sources = channel.get("epg_sources") or []
        channel_key = norm(channel_name)
        matched_keys = {channel_key} | alias_lookup.get(channel_key, set())
        matched_sources: dict[str, set[str]] = defaultdict(set)
        for key in matched_keys:
            for source_id, ids in names_to_ids.get(key, {}).items():
                matched_sources[source_id].update(ids)

        # Existing explicit and HTML-guide associations are not proposed for replacement.
        if current_id or current_sources:
            already_mapped += 1
            continue
        if channel_key in html_mapped_names:
            html_mapped += 1
            already_mapped += 1
            continue
        if not matched_sources:
            no_exact_match.append(channel_name)
            continue

        source_results = {
            source_id: sorted(ids)
            for source_id, ids in sorted(matched_sources.items())
        }
        unique = all(len(ids) == 1 for ids in source_results.values())
        if not unique:
            ambiguous += 1
        candidates.append({
            "channel_id": str(channel.get("id") or ""),
            "channel_name": channel_name,
            "normalized_name": channel_key,
            "source_ids": source_results,
            "status": "unique_exact_name_review" if unique else "ambiguous_exact_name_review",
            "automatic_update": False,
            "reason": (
                "Nome normalizado coincide exatamente; confirmar região, variante e programação antes de mapear."
                if unique else
                "Mais de um ID XMLTV corresponde ao nome; revisão manual obrigatória."
            ),
        })

    return {
        "schema_version": 1,
        "report_type": "epg_exact_name_mapping_candidates",
        "read_only": True,
        "catalog_mutated": False,
        "fuzzy_matching_used": False,
        "counts": {
            "catalog_channels": len(channels),
            "channels_with_existing_epg_association": already_mapped,
            "channels_with_existing_html_epg_mapping": html_mapped,
            "candidate_channels": len(candidates),
            "unique_exact_name_candidates": sum(c["status"] == "unique_exact_name_review" for c in candidates),
            "ambiguous_exact_name_candidates": ambiguous,
            "channels_without_exact_name_match": len(no_exact_match),
        },
        "candidates": candidates,
        "unmatched_examples": no_exact_match[:100],
        "notes": [
            "Candidates are review suggestions only; this report never edits channels.json or channel-map.json.",
            "An exact normalized name does not prove the feed carries the correct regional channel or current programmes.",
            "IDs are kept source-specific because separate XMLTV feeds can use different IDs for the same channel.",
            "No fuzzy matching, guessed IDs, or automatic reassignment is performed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/epg-mapping-candidates.json"))
    args = parser.parse_args()
    report = build_report(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "counts": report["counts"], "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
