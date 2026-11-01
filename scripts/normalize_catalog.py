#!/usr/bin/env python3
"""Normalize safe display-text formatting across channels, radios, and VOD titles."""
import html
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/channels/channels.json"
RADIOS = ROOT / "catalog/radios/radios.json"
VOD_INDEX = ROOT / "catalog/vod/index.json"
RULES = ROOT / "normalizer/rules.json"


def normalize_display_text(value):
    """Decode HTML entities and normalize whitespace without changing language shaping."""
    if not isinstance(value, str):
        return value
    value = html.unescape(value).lstrip("\ufeff")
    return re.sub(r"\s+", " ", value).strip()


def key(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value).strip().casefold()


def atomic_write_text(path, text):
    """Publish a complete file atomically; keep the old file if publication fails."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def normalize_title_records(records):
    """Normalize only title display text; preserve IDs, metadata, and source arrays."""
    updated = 0
    for item in records if isinstance(records, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("title"), str):
            continue
        normalized = normalize_display_text(item["title"])
        if normalized != item["title"]:
            item["title"] = normalized
            updated += 1
    return updated


def write_json_if_changed(path, data, compact=False):
    serialized = (
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
        if compact else json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    if path.read_text(encoding="utf-8") == serialized:
        return False
    atomic_write_text(path, serialized)
    return True


def normalize_vod_titles():
    manifest = json.loads(VOD_INDEX.read_text(encoding="utf-8"))
    categories = manifest.get("categories", {})
    detail_paths = set()
    index_records = 0
    detail_records = 0
    changed_files = 0
    for category in categories.values():
        relative = category.get("index_path") if isinstance(category, dict) else None
        if not relative:
            continue
        path = ROOT / relative
        records = json.loads(path.read_text(encoding="utf-8"))
        index_records += len(records) if isinstance(records, list) else 0
        if isinstance(records, list):
            detail_paths.update(
                item.get("detail_path") for item in records
                if isinstance(item, dict) and item.get("detail_path")
            )
        if normalize_title_records(records):
            changed_files += int(write_json_if_changed(path, records, compact=True))
    for relative in sorted(detail_paths):
        path = ROOT / relative
        records = json.loads(path.read_text(encoding="utf-8"))
        detail_records += len(records) if isinstance(records, list) else 0
        if normalize_title_records(records):
            changed_files += int(write_json_if_changed(path, records, compact=True))
    return index_records, detail_records, changed_files


def main():
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    aliases = {key(k): v for k, v in rules.get("aliases", {}).items()}
    groups = {key(k): v for k, v in rules.get("group_aliases", {}).items()}
    radio_aliases = {key(k): v for k, v in rules.get("radio_aliases", {}).items()}

    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    seen = set()
    duplicates = []
    for item in data.get("channels", []):
        name = normalize_display_text(item.get("name", ""))
        if name:
            item["name"] = aliases.get(key(name), name)
        group = normalize_display_text(item.get("group", ""))
        if group:
            item["group"] = groups.get(key(group), group)
        identity = item.get("id") or key(item.get("name"))
        if identity in seen:
            duplicates.append(identity)
        seen.add(identity)
    write_json_if_changed(CATALOG, data)

    radios = json.loads(RADIOS.read_text(encoding="utf-8"))
    for item in radios.get("radios", []):
        if not isinstance(item, dict):
            continue
        name = normalize_display_text(item.get("name", ""))
        if name:
            item["name"] = radio_aliases.get(key(name), name)
        if item.get("genre"):
            item["genre"] = normalize_display_text(item["genre"])
    write_json_if_changed(RADIOS, radios)

    index_records, detail_records, vod_files_changed = normalize_vod_titles()
    if duplicates:
        print("Possíveis IDs duplicados (não removidos): " + ", ".join(sorted(set(duplicates))))
    print(
        f"Normalizados {len(data.get('channels', []))} canais, "
        f"{len(radios.get('radios', []))} rádios, "
        f"{index_records} registros nos índices VOD e {detail_records} detalhes VOD; "
        f"{vod_files_changed} arquivos VOD alterados. Nenhum registro foi removido."
    )


if __name__ == "__main__":
    main()
