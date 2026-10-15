#!/usr/bin/env python3
"""Safe starter updater for public M3U sources listed in sources/sources.json.

Only parses enabled, explicitly registered sources. Existing catalog is preserved
if no valid items are obtained; publication is gated by validation in CI.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources/sources.json"
OUT = ROOT / "catalog/channels/channels.json"
MAX_BYTES = 20 * 1024 * 1024
TIMEOUT = 20

def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "CineHUB-ACERVO/0.1 (+catalog validator)"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("fonte excede limite de 20 MiB")
    return body.decode("utf-8-sig", errors="replace")

def parse_m3u(text, source_id, priority):
    channels, name, attrs = [], None, {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            name = line.rsplit(",", 1)[-1].strip()
            attrs = {k: v for k, v in re.findall(r'([\w-]+)="([^"]*)"', line)}
        elif line and not line.startswith("#") and name:
            channel_name = attrs.get("tvg-name") or name
            slug = re.sub(r"[^a-z0-9]+", "-", channel_name.casefold()).strip("-") or "canal"
            channels.append({
                "id": "ch-" + slug,
                "name": channel_name,
                "group": attrs.get("group-title") or "Outros",
                "logo_url": attrs.get("tvg-logo") or None,
                "epg_id": attrs.get("tvg-id") or None,
                "sources": [{"url": line, "priority": priority, "source_id": source_id}]
            })
            name, attrs = None, {}
    return channels

def main():
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    current = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"schema_version": 1, "channels": []}
    collected, failures = {}, []
    for source in sorted(cfg.get("sources", []), key=lambda s: s.get("priority", 999)):
        if not source.get("enabled") or source.get("category") != "channels":
            continue
        url = source.get("url", "")
        if not url.startswith("https://"):
            failures.append(f'{source.get("id", "?")}: URL HTTPS ausente/inválida')
            continue
        try:
            if source.get("format") not in ("m3u", "m3u8"):
                continue
            parsed = parse_m3u(fetch(url), source["id"], int(source.get("priority", 100)))
            if not parsed:
                raise ValueError("nenhum item M3U válido")
            for item in parsed:
                ident = item["id"]
                if ident not in collected:
                    collected[ident] = item
                else:
                    collected[ident]["sources"].extend(item["sources"])
        except Exception as exc:
            failures.append(f'{source.get("id", "?")}: {type(exc).__name__}: {exc}')
    if collected:
        current["channels"] = list(collected.values())
        current["generated_at"] = datetime.now(timezone.utc).isoformat()
        OUT.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Atualizados {len(collected)} canais.")
    else:
        print("Nenhuma fonte de canal válida; catálogo anterior preservado.")
    if failures:
        report = ROOT / "reports"
        report.mkdir(exist_ok=True)
        (report / "last-update.txt").write_text("\n".join(failures) + "\n", encoding="utf-8")
        print("\n".join("AVISO: " + item for item in failures))
    if not collected and any(s.get("enabled") and s.get("category") == "channels" for s in cfg.get("sources", [])):
        raise SystemExit("Nenhuma fonte ativa produziu dados; não publicar catálogo vazio.")

if __name__ == "__main__":
    main()
