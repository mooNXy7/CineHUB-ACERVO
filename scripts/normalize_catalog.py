#!/usr/bin/env python3
"""Normalize channel names and groups conservatively; never deletes records."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/channels/channels.json"
RULES = ROOT / "normalizer/rules.json"

def key(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value).strip().casefold()

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
    CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Normalizados {len(data.get('channels', []))} canais; nenhum registro foi removido.")

if __name__ == "__main__":
    main()
