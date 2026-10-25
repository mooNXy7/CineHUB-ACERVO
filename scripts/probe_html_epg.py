#!/usr/bin/env python3
"""Read-only live probe of two explicitly approved HTML EPG sources.

Fetches only one Meu Guia and one Guia de TV page, prints a small summary, and
never writes catalog files. Intended for manual GitHub Actions dispatch.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parse_html_epg import parse_guiadetv, parse_meuguia
from update_html_epg import fetch_html

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def main() -> int:
    reference_date = dt.datetime.now(SAO_PAULO).date()
    probes = [
        ("meuguia-br", "HBO", "https://meuguia.tv/programacao/canal/HBO",
         lambda body: parse_meuguia(body, reference_date=reference_date)),
        ("guia-de-tv-br", "SONY Movies", "https://www.guiadetv.com/canal/sony-movies",
         parse_guiadetv),
    ]
    report = []
    failed = False
    for source_id, channel, url, parser in probes:
        try:
            body = fetch_html(url)
            programmes = parser(body)
            report.append({
                "source_id": source_id,
                "channel": channel,
                "result": "ok" if len(programmes) >= 2 else "needs_review",
                "parsed_programmes": len(programmes),
                "sample": [
                    {"start": item["start"], "end": item["end"], "title": item["title"]}
                    for item in programmes[:3]
                ],
            })
            if len(programmes) < 2:
                failed = True
        except Exception as exc:
            report.append({
                "source_id": source_id,
                "channel": channel,
                "result": "error",
                "error": f"{type(exc).__name__}: {str(exc)[:240]}",
            })
            failed = True
    print(json.dumps({
        "mode": "read-only-live-probe",
        "timezone": "America/Sao_Paulo",
        "catalog_written": False,
        "results": report,
    }, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
