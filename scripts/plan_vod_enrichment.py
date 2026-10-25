#!/usr/bin/env python3
"""Build a read-only dry-run report for safe VOD metadata enrichment candidates."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("movies", "series", "anime", "doramas")
TARGET_FIELDS = ("poster_url", "year", "genres")
EXTERNAL_ID_FIELDS = ("tmdb_id", "imdb_id", "tvdb_id", "mal_id", "anilist_id")
DEFAULT_LIMIT = 250
MAX_LIMIT = 5000


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def safe_catalog_path(root: Path, relative: str) -> Path:
    """Resolve a manifest path while preventing reads outside the repository."""
    base = root.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"VOD index path escapes repository root: {relative}")
    return candidate


def missing_fields(record: dict[str, Any]) -> list[str]:
    missing = []
    for field in TARGET_FIELDS:
        value = record.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def external_ids(record: dict[str, Any]) -> dict[str, str]:
    found = {}
    for field in EXTERNAL_ID_FIELDS:
        value = record.get(field)
        if value not in (None, ""):
            found[field] = str(value)[:100]
    return found


def classify(record: dict[str, Any], ids: dict[str, str]) -> tuple[str, str]:
    if ids:
        return ("provider_id_present", "ID externo já existe; confirmar tipo/identidade antes de consultar o provedor.")
    if record.get("title") and record.get("year") and record.get("type"):
        return ("title_year_type_candidate", "Título, ano e tipo disponíveis; correspondência precisa de verificação.")
    return ("manual_identity_review", "Identidade insuficiente ou ambígua; revisar manualmente antes de qualquer consulta.")


def build_report(root: Path = ROOT, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    """Inventory missing metadata; never mutate catalogs or access the network."""
    if not isinstance(limit, int) or limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    manifest = load_json(root / "catalog/vod/index.json")
    categories = manifest.get("categories", {}) if isinstance(manifest, dict) else {}
    report_by_category = {}
    overall = Counter()
    for section in SECTIONS:
        info = categories.get(section, {}) if isinstance(categories, dict) else {}
        index_path = info.get("index_path", f"catalog/vod/index/{section}.json")
        records = load_json(safe_catalog_path(root, index_path))
        if not isinstance(records, list):
            raise ValueError(f"VOD index for {section} must be a JSON list")
        category_counts = Counter()
        status_counts = Counter()
        examples = []
        for record in records:
            if not isinstance(record, dict):
                continue
            missing = missing_fields(record)
            if not missing:
                continue
            ids = external_ids(record)
            status, reason = classify(record, ids)
            category_counts["records_with_missing_metadata"] += 1
            category_counts.update(f"missing_{field}" for field in missing)
            status_counts[status] += 1
            overall["records_with_missing_metadata"] += 1
            overall.update(f"missing_{field}" for field in missing)
            overall[f"status_{status}"] += 1
            if len(examples) < limit:
                examples.append({
                    "id": str(record.get("id") or "?")[:180],
                    "title": str(record.get("title") or "")[:180],
                    "category": section,
                    "type": str(record.get("type") or section)[:40],
                    "year": str(record.get("year") or "")[:20],
                    "missing_fields": missing,
                    "external_ids": ids,
                    "match_status": status,
                    "reason": reason,
                })
        report_by_category[section] = {
            "catalog_records": len(records),
            "records_with_missing_metadata": category_counts["records_with_missing_metadata"],
            "missing_field_counts": {
                field: category_counts[f"missing_{field}"] for field in TARGET_FIELDS
            },
            "match_status_counts": dict(sorted(status_counts.items())),
            "examples_included": len(examples),
            "examples_truncated": category_counts["records_with_missing_metadata"] > len(examples),
            "examples": examples,
        }
    return {
        "report_schema_version": 1,
        "report_type": "vod_metadata_enrichment_dry_run",
        "read_only": True,
        "network_accessed": False,
        "catalog_mutated": False,
        "example_limit_per_category": limit,
        "target_fields": list(TARGET_FIELDS),
        "external_id_fields_checked": list(EXTERNAL_ID_FIELDS),
        "summary": dict(sorted(overall.items())),
        "categories": report_by_category,
        "notes": [
            "Este relatório não consulta provedores nem altera o catálogo.",
            "ID externo presente não garante identidade correta; confirme tipo e correspondência.",
            "Título/ano/tipo são apenas candidatos e não autorizam atualização automática.",
            "Nenhuma URL de stream, credencial ou resposta externa é incluída.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="raiz local do repositório")
    parser.add_argument("--output", type=Path, help="arquivo JSON de saída; omisso imprime no stdout")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"máximo de exemplos por categoria (1-{MAX_LIMIT})")
    args = parser.parse_args()
    report = build_report(args.root, args.limit)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
