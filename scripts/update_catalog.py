#!/usr/bin/env python3
"""Safely refresh channel sources without replacing curated catalog metadata."""
import ipaddress
import json
import re
import urllib.request
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources/sources.json"
OUT = ROOT / "catalog/channels/channels.json"
MAX_BYTES = 20 * 1024 * 1024
TIMEOUT = 20


def safe_https_url(url):
    """Reject non-HTTPS URLs, embedded credentials, and local/private hosts."""
    try:
        parsed = urlsplit(str(url).strip())
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
            return False
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return True
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or
                    ip.is_reserved or ip.is_multicast or ip.is_unspecified)
    except (TypeError, ValueError):
        return False


def fetch(url):
    if not safe_https_url(url):
        raise ValueError("URL da fonte não passou na validação HTTPS/host")
    request = urllib.request.Request(
        url, headers={"User-Agent": "CineHUB-ACERVO/0.2 (+catalog validator)"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        if response.geturl() and not safe_https_url(response.geturl()):
            raise ValueError("redirecionamento para URL não segura")
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("fonte excede limite de 20 MiB")
    return body.decode("utf-8-sig", errors="replace")


def normalize_key(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip().casefold()


def parse_m3u(text, source_id, priority):
    channels, name, attrs = [], None, {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            name = line.rsplit(",", 1)[-1].strip()
            attrs = {k: v for k, v in re.findall(r'([\w-]+)="([^"]*)"', line)}
        elif line and not line.startswith("#") and name:
            channel_name = (attrs.get("tvg-name") or name).strip()
            if safe_https_url(line) and channel_name:
                slug = re.sub(r"[^a-z0-9]+", "-", channel_name.casefold()).strip("-") or "canal"
                channels.append({
                    "id": "ch-" + slug,
                    "name": channel_name,
                    "group": attrs.get("group-title") or "Outros",
                    "logo_url": attrs.get("tvg-logo") if safe_https_url(attrs.get("tvg-logo", "")) else None,
                    "epg_id": attrs.get("tvg-id") or None,
                    "sources": [{"url": line, "priority": priority, "source_id": source_id}]
                })
            name, attrs = None, {}
    return channels


def merge_channels(existing, incoming):
    """Keep existing records/metadata and append only new, deduplicated stream URLs."""
    result = list(existing)
    by_id = {str(item.get("id")): item for item in result if item.get("id")}
    by_name = {normalize_key(item.get("name")): item for item in result if item.get("name")}
    added_sources = 0
    for item in incoming:
        target = by_id.get(str(item.get("id"))) or by_name.get(normalize_key(item.get("name")))
        if target is None:
            clone = dict(item)
            clone["sources"] = list(item.get("sources") or [])
            result.append(clone)
            if clone.get("id"):
                by_id[str(clone["id"])] = clone
            if clone.get("name"):
                by_name[normalize_key(clone["name"])] = clone
            continue
        existing_sources = target.setdefault("sources", [])
        known_urls = {s.get("url") for s in existing_sources if isinstance(s, dict)}
        for source in item.get("sources") or []:
            if source.get("url") not in known_urls:
                existing_sources.append(source)
                known_urls.add(source.get("url"))
                added_sources += 1
        # Fill only blank metadata; never replace curated values with source values.
        for field in ("group", "logo_url", "epg_id"):
            if not target.get(field) and item.get(field):
                target[field] = item[field]
    return result, added_sources


def main():
    cfg = json.loads(SOURCES.read_text(encoding="utf-8"))
    current = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {
        "schema_version": 1, "channels": []
    }
    collected, failures = {}, []
    active = [s for s in cfg.get("sources", [])
              if s.get("enabled") and s.get("category") == "channels"]
    for source in sorted(active, key=lambda s: s.get("priority", 999)):
        url = source.get("url", "")
        if not safe_https_url(url):
            failures.append(f'{source.get("id", "?")}: URL HTTPS ausente/inválida')
            continue
        try:
            if source.get("format") not in ("m3u", "m3u8"):
                failures.append(f'{source.get("id", "?")}: formato não suportado')
                continue
            parsed = parse_m3u(fetch(url), source["id"], int(source.get("priority", 100)))
            if not parsed:
                raise ValueError("nenhum item com stream HTTPS seguro")
            for item in parsed:
                ident = item["id"]
                if ident not in collected:
                    collected[ident] = item
                else:
                    collected[ident]["sources"].extend(item["sources"])
        except Exception as exc:
            failures.append(f'{source.get("id", "?")}: {type(exc).__name__}: {exc}')

    if collected:
        current["channels"], added = merge_channels(
            current.get("channels", []), list(collected.values())
        )
        current["generated_at"] = datetime.now(timezone.utc).isoformat()
        OUT.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        print(f"Fonte(s) processada(s): {len(collected)} canais; {added} fontes anexadas.")
    else:
        print("Nenhuma fonte de canal segura válida; catálogo anterior preservado.")

    report = ROOT / "reports"
    report.mkdir(exist_ok=True)
    report_path = report / "last-update.txt"
    if failures:
        report_path.write_text("\\n".join(failures) + "\\n", encoding="utf-8")
        print("\\n".join("AVISO: " + item for item in failures))
    elif active and report_path.exists():
        report_path.unlink()

    if active and not collected:
        raise SystemExit("Nenhuma fonte ativa produziu dados seguros; catálogo não alterado.")


if __name__ == "__main__":
    main()
