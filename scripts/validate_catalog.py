#!/usr/bin/env python3
"""Validate catalog schemas, VOD category indexes, stable IDs, and detail references."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "channels": ROOT / "catalog/channels/channels.json",
    "radios": ROOT / "catalog/radios/radios.json",
    "vod": ROOT / "catalog/vod/index.json",
    "sources": ROOT / "sources/sources.json",
}


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def main():
    errors = []
    loaded = {}
    for name, path in FILES.items():
        try:
            data = load(path)
            loaded[name] = data
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            errors.append(f"{path.relative_to(ROOT)}: schema_version deve ser 1")
            continue
        key = {"channels": "channels", "radios": "radios", "vod": None, "sources": "sources"}[name]
        if key and not isinstance(data.get(key), list):
            errors.append(f"{path.relative_to(ROOT)}: '{key}' deve ser uma lista")
        if name == "vod":
            categories = data.get("categories")
            if categories is not None and not isinstance(categories, dict):
                errors.append(f"{path.relative_to(ROOT)}: 'categories' deve ser um objeto")

    vod = loaded.get("vod", {})
    if isinstance(vod, dict):
        sections = ("movies", "series", "anime", "doramas")
        categories = vod.get("categories", {})
        for section in sections:
            if isinstance(categories, dict) and isinstance(categories.get(section), dict):
                category_info = categories[section]
                index_path = category_info.get("index_path")
                path = ROOT / index_path if index_path else None
                if path is None or not path.exists():
                    errors.append(f"catalog/vod/index.json: índice de categoria ausente {index_path}")
                    items = []
                else:
                    try:
                        items = load(path)
                    except (OSError, json.JSONDecodeError) as exc:
                        errors.append(f"{path.relative_to(ROOT)}: {exc}")
                        items = []
                if isinstance(items, list) and category_info.get("count") != len(items):
                    errors.append(f"{index_path}: contagem não corresponde ao manifesto")
            else:
                # Compatibilidade com o formato inicial, que guardava arrays no manifesto.
                items = vod.get(section, [])
            ids = set()
            for item in items if isinstance(items, list) else []:
                ident = item.get("id") if isinstance(item, dict) else None
                if not ident:
                    errors.append(f"índice VOD: item sem id em {section}")
                    continue
                if ident in ids:
                    errors.append(f"índice VOD: ID duplicado {ident} em {section}")
                ids.add(ident)
                detail = item.get("detail_path")
                if detail:
                    path = ROOT / detail
                    if not path.exists():
                        errors.append(f"índice VOD: detalhe ausente {detail}")
        details_root = ROOT / "catalog/vod/details"
        if details_root.exists():
            for section in sections:
                for path in (details_root / section).glob("*.json"):
                    try:
                        records = load(path)
                    except (OSError, json.JSONDecodeError) as exc:
                        errors.append(f"{path.relative_to(ROOT)}: {exc}")
                        continue
                    if not isinstance(records, list):
                        errors.append(f"{path.relative_to(ROOT)}: o detalhe deve ser uma lista")
                        continue
                    record_ids = [x.get("id") for x in records if isinstance(x, dict)]
                    if len(record_ids) != len(set(record_ids)):
                        errors.append(f"{path.relative_to(ROOT)}: IDs duplicados no arquivo")

    if errors:
        print("\n".join("ERROR: " + error for error in errors))
        raise SystemExit(1)
    print(f"OK: {len(FILES)} catálogos principais e shards VOD válidos")


if __name__ == "__main__":
    main()
