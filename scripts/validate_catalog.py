#!/usr/bin/env python3
"""Validate the lightweight CineHUB ACERVO JSON catalog files."""
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
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def main():
    errors = []
    for name, path in FILES.items():
        try:
            data = load(path)
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
            for section in ("movies", "series", "anime", "doramas"):
                if not isinstance(data.get(section), list):
                    errors.append(f"{path.relative_to(ROOT)}: '{section}' deve ser uma lista")
    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        raise SystemExit(1)
    print(f"OK: {len(FILES)} arquivos de catálogo válidos")

if __name__ == "__main__":
    main()
