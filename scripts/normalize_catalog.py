#!/usr/bin/env python3
"""Normalize channel names and groups conservatively; never deletes records."""
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/channels/channels.json"
RULES = ROOT / "normalizer/rules.json"


def key(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\\s+", " ", value).strip().casefold()


def atomic_write_text(path, text):
    """Publish a complete file atomically; keep the old file if publication fails."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\\n") as stream:
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


def main():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    aliases = {key(k): v for k, v in rules.get("aliases", {}).items()}
    groups = {key(k): v for k, v in rules.get("group_aliases", {}).items()}
    seen = set()
    duplicates = []
    for item in data.get("channels", []):
        name = str(item.get("name", "")).strip()
        if name:
            item["name"] = aliases.get(key(name), name)
        group = str(item.get("group", "")).strip()
        if group:
            item["group"] = groups.get(key(group), group)
        identity = item.get("id") or key(item.get("name"))
        if identity in seen:
            duplicates.append(identity)
        seen.add(identity)
    if duplicates:
        print("Possíveis IDs duplicados (não removidos): " + ", ".join(sorted(set(duplicates))))
    atomic_write_text(CATALOG, json.dumps(data, ensure_ascii=False, indent=2) + "\\n")
    print(f"Normalizados {len(data.get('channels', []))} canais; nenhum registro foi removido.")


if __name__ == "__main__":
    main()
