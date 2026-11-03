#!/usr/bin/env python3
"""Import a real ACERVO input format into an isolated canonical candidate document."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from acervo_v2.importers import (
    parse_channels_json, parse_epg_mapping, parse_epg_sources, parse_m3u,
    parse_radios_json, parse_radios_text, parse_source_registry, parse_vod_catalog,
    parse_vod_reference_movies, parse_vod_reference_series,
)
from acervo_v2.xmltv import parse_xmltv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", required=True, choices=(
        "channels-json", "m3u", "radios-json", "radio-pipe", "vod-json",
        "vod-reference-movies", "vod-reference-series", "epg-sources-json",
        "epg-map-json", "source-registry-json", "xmltv",
    ))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-ref", default=None)
    parser.add_argument("--output", type=Path, default=Path("staging/phase-b/import.candidate.json"))
    args = parser.parse_args()

    raw = args.input.read_bytes()
    text = raw.decode("utf-8-sig")
    document = json.loads(text) if args.format.endswith("-json") or args.format == "vod-json" else None
    source_ref = args.source_ref or args.input.as_posix()
    extra = {}
    if args.format == "channels-json":
        domain, records, quarantine = "channels", *parse_channels_json(document, args.source_id, source_ref)
    elif args.format == "m3u":
        domain, records, quarantine = "channels", *parse_m3u(text, args.source_id, source_ref)
    elif args.format == "radios-json":
        domain, records, quarantine = "radios", *parse_radios_json(document, args.source_id, source_ref)
    elif args.format == "radio-pipe":
        domain, records, quarantine = "radios", *parse_radios_text(text, args.source_id, source_ref)
    elif args.format == "vod-json":
        domain, records, quarantine = "vod", *parse_vod_catalog(args.root, args.source_id)
    elif args.format == "vod-reference-movies":
        domain, records, quarantine = "vod", *parse_vod_reference_movies(text, args.source_id, source_ref)
    elif args.format == "vod-reference-series":
        domain, records, quarantine = "vod", *parse_vod_reference_series(text, args.source_id, source_ref)
    elif args.format == "epg-sources-json":
        domain, records, quarantine = "epg-sources", *parse_epg_sources(document, args.source_id)
    elif args.format == "epg-map-json":
        domain, records, quarantine = "epg-mappings", *parse_epg_mapping(document, args.source_id)
    elif args.format == "source-registry-json":
        domain, records, quarantine = "sources", *parse_source_registry(document, args.source_id)
    else:
        domain = "epg-programmes"
        channels, records, quarantine = parse_xmltv(raw, args.source_id, source_ref)
        extra["epg_channels"] = channels

    result = {
        "schema_version": 1, "domain": domain, "records": records,
        "quarantine": quarantine, "metadata": {
            "source_id": args.source_id, "source_ref": source_ref,
            "input_bytes": len(raw), "record_count": len(records),
            "quarantine_count": len(quarantine), **extra,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if domain == "epg-programmes":
        channel_document = {"schema_version": 1, "domain": "epg-channels",
                            "records": extra.get("epg_channels", []), "quarantine": []}
        (args.output.parent / "epg-channels.json").write_text(
            json.dumps(channel_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({"output": str(args.output), "domain": domain,
                      "records": len(records), "quarantine": len(quarantine)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
