#!/usr/bin/env python3
"""Validate catalog schemas, VOD category indexes, stable IDs, and detail references."""
import datetime as dt
import ipaddress
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

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


def safe_source_url(value):
    """Structural URL check for configured network sources (no network/DNS lookup)."""
    try:
        parsed = urlsplit(str(value or "").strip())
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.port not in (None, 443):
            return False
        sensitive = {"token", "access_token", "auth", "authorization", "password",
                     "passwd", "username", "user", "key", "signature", "sig", "session"}
        if any(key.lower() in sensitive for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and (
            address.is_private or address.is_loopback or address.is_link_local
            or address.is_reserved or address.is_multicast or address.is_unspecified
        ):
            return False
        return True
    except (TypeError, ValueError):
        return False


def is_http_url(value):
    try:
        parsed = urlsplit(str(value or "").strip())
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
    except (TypeError, ValueError):
        return False


def validate_radio_catalog(radios, quarantine):
    """Ensure malformed URL-as-name rows stay outside the active radio catalog."""
    errors = []
    active = radios.get("radios", []) if isinstance(radios, dict) else []
    quarantined = quarantine.get("records", []) if isinstance(quarantine, dict) else []
    if not isinstance(active, list):
        return ["catalog/radios/radios.json: radios deve ser uma lista"]
    if not isinstance(quarantined, list):
        return ["catalog/radios/quarantine.json: records deve ser uma lista"]
    active_ids = set()
    for item in active:
        if not isinstance(item, dict):
            errors.append("catalog/radios/radios.json: registro de rádio inválido")
            continue
        if is_http_url(item.get("name")):
            errors.append(
                f"catalog/radios/radios.json: URL no campo name do registro {item.get('id', '?')}"
            )
        if item.get("id"):
            active_ids.add(str(item["id"]))
    quarantine_ids = set()
    for item in quarantined:
        if not isinstance(item, dict) or not item.get("id"):
            errors.append("catalog/radios/quarantine.json: registro sem objeto/id válido")
            continue
        ident = str(item["id"])
        if ident in quarantine_ids:
            errors.append(f"catalog/radios/quarantine.json: ID duplicado {ident}")
        quarantine_ids.add(ident)
        if not is_http_url(item.get("name")):
            errors.append(f"catalog/radios/quarantine.json: registro {ident} não tem URL no name")
    overlap = active_ids & quarantine_ids
    if overlap:
        errors.append(
            "catalog/radios: IDs presentes no catálogo ativo e na quarentena: "
            + ", ".join(sorted(overlap)[:10])
        )
    return errors


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


def index_detail_tmdb_mismatches(indexed: dict, detail_records: list, section: str) -> list[str]:
    """Return TMDB ID disagreements between the compact index and detail shards."""
    mismatches = []
    for record in detail_records:
        if not isinstance(record, dict) or not record.get("id"):
            continue
        item = indexed.get(str(record["id"]))
        if item is None:
            continue
        index_has_id = "tmdb_id" in item and item.get("tmdb_id") not in (None, "")
        detail_has_id = record.get("tmdb_id") not in (None, "")
        index_id = str(item.get("tmdb_id") or "").strip()
        detail_id = str(record.get("tmdb_id") or "").strip()
        if index_has_id != detail_has_id or index_id != detail_id:
            mismatches.append(
                f"{section}: índice/detalhe divergem em tmdb_id para {record['id']} "
                f"(index={index_id or 'ausente'}, detail={detail_id or 'ausente'})"
            )
    return mismatches


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

    radio_quarantine_path = ROOT / "catalog/radios/quarantine.json"
    try:
        radio_quarantine = load(radio_quarantine_path)
        if not isinstance(radio_quarantine, dict) or radio_quarantine.get("schema_version") != 1:
            errors.append("catalog/radios/quarantine.json: schema_version deve ser 1")
        else:
            errors.extend(validate_radio_catalog(loaded.get("radios", {}), radio_quarantine))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{radio_quarantine_path.relative_to(ROOT)}: {exc}")

    # Validate network source endpoints before any updater can fetch them.
    for source_doc_name, url_fields in (
        ("epg_sources", ("url", "probe_url")),
        ("sources", ("url",)),
    ):
        source_doc = loaded.get(source_doc_name, {})
        if not isinstance(source_doc, dict):
            continue
        for source in source_doc.get("sources", []):
            if not isinstance(source, dict) or not source.get("enabled", False):
                continue
            for field in url_fields:
                endpoint = source.get(field)
                if endpoint and not safe_source_url(endpoint):
                    errors.append(
                        f"{FILES[source_doc_name].relative_to(ROOT)}: URL insegura/inválida "
                        f"para fonte {source.get('id', '?')} ({field})"
                    )
        if source_doc_name == "epg_sources":
            for source in source_doc.get("sources", []):
                if not isinstance(source, dict) or not source.get("enabled", False):
                    continue
                template = source.get("url_template")
                if template:
                    base = template.split("{", 1)[0]
                    if not safe_source_url(base):
                        errors.append(
                            f"{FILES[source_doc_name].relative_to(ROOT)}: url_template inseguro "
                            f"para fonte {source.get('id', '?')}"
                        )

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
        index_by_section: dict[str, dict[str, dict]] = {}
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
            index_by_section[section] = {
                str(item.get("id")): item
                for item in items if isinstance(item, dict) and item.get("id")
            } if isinstance(items, list) else {}
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
                    errors.extend(index_detail_tmdb_mismatches(
                        index_by_section.get(section, []), records, section
                    ))

    if errors:
        print("\n".join("ERROR: " + error for error in errors))
        raise SystemExit(1)
    print(f"OK: {len(FILES)} catálogos principais, fontes EPG e shards VOD válidos")


if __name__ == "__main__":
    main()
