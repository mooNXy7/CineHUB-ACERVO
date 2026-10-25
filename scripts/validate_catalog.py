#!/usr/bin/env python3
"""Validate catalog schemas, VOD category indexes, stable IDs, and detail references."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "channels": ROOT / "catalog/channels/channels.json",
    "radios": ROOT / "catalog/radios/radios.json",
    "vod": ROOT / "catalog/vod/index.json",
    "sources": ROOT / "sources/sources.json",
    "epg_sources": ROOT / "catalog/epg/sources.json",
    "epg_map": ROOT / "catalog/epg/channel-map.json",
}


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_html_epg_doc(data):
    """Return structural errors for the optional HTML EPG sidecar."""
    errors = []
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return ["catalog/epg/html-programmes.json: schema_version deve ser 1"]
    if data.get("timezone") != "America/Sao_Paulo":
        errors.append("catalog/epg/html-programmes.json: timezone deve ser America/Sao_Paulo")
    programmes = data.get("programmes")
    health = data.get("health")
    if not isinstance(programmes, dict) or not isinstance(health, dict):
        return errors + ["catalog/epg/html-programmes.json: programmes e health devem ser objetos"]
    for channel, record in programmes.items():
        if not isinstance(record, dict) or not isinstance(record.get("programmes"), list):
            errors.append(f"html EPG {channel}: programmes deve ser uma lista")
            continue
        if record.get("source_id") not in {"meuguia-br", "guia-de-tv-br"}:
            errors.append(f"html EPG {channel}: source_id inválido")
        previous_start = None
        for item in record["programmes"]:
            if not isinstance(item, dict) or not item.get("title"):
                errors.append(f"html EPG {channel}: programa sem título")
                continue
            try:
                start = dt.datetime.fromisoformat(item["start"])
                end = dt.datetime.fromisoformat(item["end"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"html EPG {channel}: start/end inválidos")
                continue
            if start.tzinfo is None or end.tzinfo is None or end <= start:
                errors.append(f"html EPG {channel}: intervalo inválido ou sem fuso")
            if previous_start is not None and start < previous_start:
                errors.append(f"html EPG {channel}: programas fora de ordem")
            previous_start = start
    return errors


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
        key = {"channels": "channels", "radios": "radios", "vod": None, "sources": "sources", "epg_sources": "sources", "epg_map": None}[name]
        if key and not isinstance(data.get(key), list):
            errors.append(f"{path.relative_to(ROOT)}: '{key}' deve ser uma lista")
        if name == "vod":
            categories = data.get("categories")
            if categories is not None and not isinstance(categories, dict):
                errors.append(f"{path.relative_to(ROOT)}: 'categories' deve ser um objeto")

    epg_sources = loaded.get("epg_sources", {})
    if isinstance(epg_sources, dict):
        source_ids = [x.get("id") for x in epg_sources.get("sources", []) if isinstance(x, dict)]
        if len(source_ids) != len(set(source_ids)):
            errors.append("catalog/epg/sources.json: IDs de fonte duplicados")
        priorities = [x.get("priority") for x in epg_sources.get("sources", []) if isinstance(x, dict)]
        if priorities != sorted(priorities):
            errors.append("catalog/epg/sources.json: fontes devem estar ordenadas por prioridade")
    html_epg_path = ROOT / "catalog/epg/html-programmes.json"
    if html_epg_path.exists():
        try:
            errors.extend(validate_html_epg_doc(load(html_epg_path)))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{html_epg_path.relative_to(ROOT)}: {exc}")

    epg_map = loaded.get("epg_map", {})
    if isinstance(epg_map, dict):
        for key in ("meuguia_codes", "guiadetv_slugs", "xmltv_aliases"):
            if not isinstance(epg_map.get(key), dict):
                errors.append(f"catalog/epg/channel-map.json: '{key}' deve ser um objeto")

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
    print(f"OK: {len(FILES)} catálogos principais, fontes EPG e shards VOD válidos")


if __name__ == "__main__":
    main()
