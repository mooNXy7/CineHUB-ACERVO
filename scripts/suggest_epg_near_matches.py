#!/usr/bin/env python3
"""Generate conservative, read-only near-name EPG candidates for manual review.

This is separate from the exact-match mapper. It never writes channel IDs and
only emits a candidate when the best normalized-name similarity is high and
clearly separated from the runner-up.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MIN_SCORE = 0.88
MIN_MARGIN = 0.06


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    value = re.sub(r"\b(?:hd|sd|fhd|uhd|4k|br)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(root: Path = ROOT) -> dict[str, Any]:
    channels_doc = load_json(root / "catalog/channels/channels.json")
    index_doc = load_json(root / "catalog/epg/xmltv-channels.json")
    map_doc = load_json(root / "catalog/epg/channel-map.json")
    aliases = map_doc.get("xmltv_aliases", {})
    mapped_html = {
        norm(name)
        for name in list((map_doc.get("meuguia_codes") or {}))
        + list((map_doc.get("guiadetv_slugs") or {}))
    }

    display_by_key: dict[str, dict[str, set[str]]] = {}
    for source_id, source in (index_doc.get("sources") or {}).items():
        if not isinstance(source, dict):
            continue
        for item in source.get("channels", []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            for display in item.get("display_names", []):
                key = norm(display)
                if not key:
                    continue
                display_by_key.setdefault(key, {}).setdefault(str(source_id), set()).add(str(item["id"]).strip())

    # Exact aliases are excluded here because the exact matcher owns those.
    alias_keys = set()
    for canonical, values in aliases.items():
        keys = {norm(canonical)}
        if isinstance(values, list):
            keys.update(norm(v) for v in values if norm(v))
        alias_keys.update(k for k in keys if k)

    indexed = [(key, key.split(), sources) for key, sources in display_by_key.items()]
    candidates = []
    unmatched = 0
    skipped_low_score = 0
    skipped_ambiguous = 0
    for channel in channels_doc.get("channels", []):
        if not isinstance(channel, dict):
            continue
        name = str(channel.get("name") or "").strip()
        key = norm(name)
        if not name or channel.get("epg_id") or channel.get("epg_sources"):
            continue
        if key in mapped_html or key in alias_keys or key in display_by_key:
            continue

        scored = []
        tokens = set(key.split())
        for candidate_key, candidate_tokens, sources in indexed:
            if not candidate_key or candidate_key == key:
                continue
            candidate_set = set(candidate_tokens)
            if not tokens or not candidate_set:
                continue
            # Require meaningful token overlap before calculating a full score.
            overlap = len(tokens & candidate_set) / max(1, len(tokens | candidate_set))
            if overlap < 0.5:
                continue
            score = SequenceMatcher(None, key, candidate_key).ratio()
            if score >= MIN_SCORE:
                scored.append((score, candidate_key, sources))
        scored.sort(key=lambda row: row[0], reverse=True)
        if not scored:
            unmatched += 1
            skipped_low_score += 1
            continue
        best = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        if best[0] - second_score < MIN_MARGIN:
            skipped_ambiguous += 1
            continue
        source_ids = {
            source_id: sorted(ids)
            for source_id, ids in sorted(best[2].items())
        }
        candidates.append({
            "channel_id": str(channel.get("id") or ""),
            "channel_name": name,
            "suggested_xmltv_name": best[1],
            "similarity": round(best[0], 4),
            "runner_up_similarity": round(second_score, 4),
            "source_ids": source_ids,
            "status": "near_name_manual_review",
            "automatic_update": False,
            "reason": "Nome parecido, não equivalente garantido; confirmar região, canal e programação antes de mapear.",
        })

    candidates.sort(key=lambda item: (-item["similarity"], item["channel_name"].casefold()))
    return {
        "schema_version": 1,
        "report_type": "epg_near_name_mapping_candidates",
        "read_only": True,
        "catalog_mutated": False,
        "thresholds": {"minimum_similarity": MIN_SCORE, "minimum_margin_over_runner_up": MIN_MARGIN},
        "counts": {
            "catalog_channels": len(channels_doc.get("channels", [])),
            "candidate_channels": len(candidates),
            "skipped_ambiguous": skipped_ambiguous,
            "without_high_confidence_near_match": unmatched,
        },
        "candidates": candidates,
        "notes": [
            "All near-name candidates require manual review and never modify catalog mappings.",
            "Similarity is a triage heuristic, not proof that the channel identity or regional feed matches.",
            "Source-specific XMLTV IDs are preserved; no ID is guessed or merged across feeds.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/epg-near-match-candidates.json"))
    args = parser.parse_args()
    report = build_report(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "counts": report["counts"],
                      "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
