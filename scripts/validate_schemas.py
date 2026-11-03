#!/usr/bin/env python3
"""Validate all versioned JSON Schemas and optionally a generated candidate directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = sorted((ROOT / "schemas").rglob("*.schema.json"))
CANDIDATE_SCHEMAS = {
    "vod.json": "vod/v1.schema.json",
    "channels.json": "channels/v1.schema.json",
    "radios.json": "radios/v1.schema.json",
    "logos.json": "logos/v1.schema.json",
    "sources.json": "sources/v1.schema.json",
    "epg-sources.json": "epg/sources-v1.schema.json",
    "epg-mappings.json": "epg/mappings-v1.schema.json",
    "epg-channels.json": "epg/channels-v1.schema.json",
    "epg-programmes.json": "epg/programmes-v1.schema.json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path)
    args = parser.parse_args()
    errors = []
    schemas = {}
    for path in SCHEMA_FILES:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            schemas[path.relative_to(ROOT / "schemas").as_posix()] = schema
        except Exception as exc:
            errors.append(str(path.relative_to(ROOT)) + ": " + str(exc))
    registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in schemas.values())
    if args.candidate_dir:
        for filename, schema_name in CANDIDATE_SCHEMAS.items():
            path = args.candidate_dir / filename
            if not path.exists():
                errors.append("candidate missing: " + filename)
                continue
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                validator = Draft202012Validator(schemas[schema_name], format_checker=FormatChecker(), registry=registry)
                for error in validator.iter_errors(document):
                    errors.append(filename + ": " + "/".join(str(x) for x in error.absolute_path) + ": " + error.message)
            except Exception as exc:
                errors.append(filename + ": " + str(exc))
    if errors:
        print("\n".join("ERROR: " + error for error in errors))
        raise SystemExit(1)
    print("OK: " + str(len(SCHEMA_FILES)) + " JSON Schemas validated" +
          ("; candidate documents valid" if args.candidate_dir else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
