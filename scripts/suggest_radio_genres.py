#!/usr/bin/env python3
"""Build conservative, read-only radio genre suggestions from station names."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RADIOS_FILE = "catalog/radios/radios.json"

# Adapted as transparent matching data from the authorized Saimo Android TV
# reference. Generic terms are deliberately excluded to limit false positives.
RULES = {
    "Rock": ("rock", "metal", "kiss", "punk"),
    "Notícias": ("news", "noticia", "cbn", "gaucha", "itatiaia", "tupi",
                 "esporte", "jornal", "bandnews", "radio globo", "eldorado",
                 "bandeirantes"),
    "Gospel": ("gospel", "evangel", "catolic", "crista", "louvor", "aleluia",
               "cancao nova", "novo tempo", "aparecida", "deus", "jesus",
               "igreja", "biblia"),
    "Pop": ("pop", "hits", "dance", "mix", "jovem pan", "transamerica",
            "energia", "eletro", "club", "pulse"),
    "Brasileira": ("sertanej", "mpb", "samba", "pagode", "forro", "nativa",
                   "caipira", "brega", "axe", "piseiro", "moda de viola"),
    "Clássica/Instrumental": ("classic", "jazz", "cultura", "educativa",
                              "universit", "instrumental", "blues", "lounge"),
}


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def build_report(root: Path = ROOT) -> dict[str, Any]:
    document = json.loads((root / RADIOS_FILE).read_text(encoding="utf-8"))
    radios = document.get("radios", [])
    suggestions = []
    ambiguous = []
    missing = 0
    for radio in radios:
        if not isinstance(radio, dict):
            continue
        name = str(radio.get("name") or "").strip()
        if not name:
            continue
        if str(radio.get("genre") or "").strip():
            continue
        missing += 1
        normalized = f" {norm(name)} "
        matched = [
            genre for genre, keywords in RULES.items()
            if any(f" {norm(keyword)} " in normalized for keyword in keywords)
        ]
        if len(matched) == 1:
            suggestions.append({
                "radio_id": str(radio.get("id") or ""),
                "radio_name": name,
                "suggested_genre": matched[0],
                "matched_rule_keywords": [
                    keyword for keyword in RULES[matched[0]]
                    if f" {norm(keyword)} " in normalized
                ],
                "status": "name_keyword_review",
                "automatic_update": False,
            })
        elif len(matched) > 1:
            ambiguous.append({
                "radio_id": str(radio.get("id") or ""),
                "radio_name": name,
                "candidate_genres": matched,
                "automatic_update": False,
            })

    return {
        "schema_version": 1,
        "report_type": "review_only_radio_genre_suggestions",
        "read_only": True,
        "catalog_mutated": False,
        "source": "https://github.com/SaimoTV/SaimoTV-Android",
        "matching": "accent-insensitive station-name keyword rules; no stream inspection",
        "counts": {
            "catalog_radios": len(radios),
            "radios_missing_genre_examined": missing,
            "candidate_suggestions": len(suggestions),
            "ambiguous_candidates": len(ambiguous),
            "no_keyword_match": missing - len(suggestions) - len(ambiguous),
        },
        "suggestions": suggestions,
        "ambiguous": ambiguous,
        "notes": [
            "Suggestions only; no genre is written into the catalog.",
            "Station names can be misleading; review before applying.",
            "No stream URLs, logos, headers, or playback data are imported from the reference.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/radio-genre-suggestions.json"))
    args = parser.parse_args()
    report = build_report(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "counts": report["counts"],
                      "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
