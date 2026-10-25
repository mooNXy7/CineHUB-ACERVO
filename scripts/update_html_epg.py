#!/usr/bin/env python3
"""Fetch explicitly mapped HTML EPG schedules into a separate, guarded sidecar.

This never changes channels.json or the XMLTV index. Empty or failed fetches do
not erase previously published schedules. Network access is bounded and limited
to the explicit mappings in catalog/epg/channel-map.json.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Any

from parse_html_epg import parse_guiadetv, parse_meuguia

ROOT = Path(__file__).resolve().parents[1]
EPG_DIR = ROOT / "catalog/epg"
MAP_FILE = EPG_DIR / "channel-map.json"
OUTPUT_FILE = EPG_DIR / "html-programmes.json"
USER_AGENT = "CineHUB-ACERVO-EPG/1.0 (+https://github.com/mooNXy7/CineHUB-ACERVO)"
TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_WORKERS = 4


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def fetch_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        status = getattr(response, "status", 200)
        if not 200 <= status < 300:
            raise ValueError(f"HTTP status {status}")
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and "html" not in content_type and "xhtml" not in content_type:
            raise ValueError(f"unexpected content type: {content_type[:100]}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise ValueError("HTML response exceeds 5 MiB safety limit")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def _job(source: str, name: str, code: str, fetcher: Callable[[str], str]) -> tuple[str, str, list[dict[str, Any]], str | None]:
    if source == "meuguia-br":
        url = "https://meuguia.tv/programacao/canal/" + urllib.parse.quote(code, safe="")
        parser = parse_meuguia
    else:
        url = "https://www.guiadetv.com/canal/" + urllib.parse.quote(code, safe="-")
        parser = parse_guiadetv
    try:
        document = fetcher(url)
        programmes = parser(document)
        if not programmes:
            raise ValueError("no programme entries parsed; keeping last known-good schedule")
        return source, name, programmes, None
    except Exception as exc:
        return source, name, [], f"{type(exc).__name__}: {str(exc)[:240]}"


def update_document(root: Path = ROOT, fetcher: Callable[[str], str] = fetch_html, now: dt.datetime | None = None) -> dict[str, Any]:
    epg_dir = root / "catalog/epg"
    mapping = read_json(epg_dir / "channel-map.json", {})
    previous = read_json(epg_dir / "html-programmes.json", {
        "schema_version": 1, "timezone": "America/Sao_Paulo", "programmes": {}, "health": {}
    })
    programmes_by_channel = dict(previous.get("programmes") or {})
    health_by_channel = dict(previous.get("health") or {})
    stamp = (now or dt.datetime.now(dt.timezone.utc)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    jobs: list[tuple[str, str, str]] = []
    for name, code in (mapping.get("meuguia_codes") or {}).items():
        if isinstance(name, str) and isinstance(code, str) and name.strip() and code.strip():
            jobs.append(("meuguia-br", name, code))
    for name, slug in (mapping.get("guiadetv_slugs") or {}).items():
        # Guia de TV is a fallback: only fetch it when MeuGuia did not yield a
        # current schedule in this run and there is no last-known-good schedule.
        if isinstance(name, str) and isinstance(slug, str) and name.strip() and slug.strip():
            jobs.append(("guia-de-tv-br", name, slug))

    results: dict[tuple[str, str], tuple[list[dict[str, Any]], str | None]] = {}
    # Refresh primary source on every run, even for channels with cached data.
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_job, source, name, code, fetcher): (source, name)
            for source, name, code in jobs if source == "meuguia-br"
        }
        for future in concurrent.futures.as_completed(futures):
            source, name, items, error = future.result()
            results[(source, name)] = (items, error)

    meuguia_success: set[str] = set()
    for (source, name), (items, error) in results.items():
        if source == "meuguia-br" and items:
            programmes_by_channel[name] = {
                "source_id": source, "fetched_at": stamp, "programmes": items
            }
            health_by_channel[name] = {
                "source_id": source, "checked_at": stamp, "status": "healthy",
                "programme_count": len(items), "error": None,
            }
            meuguia_success.add(name)
        elif source == "meuguia-br":
            old = health_by_channel.get(name, {})
            health_by_channel[name] = {
                "source_id": source, "checked_at": stamp,
                "status": "stale" if name in programmes_by_channel else "unavailable",
                "programme_count": len((programmes_by_channel.get(name) or {}).get("programmes", [])),
                "consecutive_failures": int(old.get("consecutive_failures", 0)) + 1,
                "error": error,
            }

    # Refresh fallback pages whenever the primary source did not produce a
    # current schedule. A successful primary result always retains precedence;
    # a fallback failure never erases the last known-good schedule.
    fallback_names = {
        name for source, name, _ in jobs
        if source == "guia-de-tv-br" and name not in meuguia_success
    }
    fallback_jobs = [
        (source, name, code) for source, name, code in jobs
        if source == "guia-de-tv-br" and name in fallback_names
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_job, source, name, code, fetcher): (source, name)
            for source, name, code in fallback_jobs
        }
        for future in concurrent.futures.as_completed(futures):
            source, name, items, error = future.result()
            if items:
                programmes_by_channel[name] = {
                    "source_id": source, "fetched_at": stamp, "programmes": items
                }
                health_by_channel[name] = {
                    "source_id": source, "checked_at": stamp, "status": "healthy",
                    "programme_count": len(items), "error": None,
                }
            else:
                old = health_by_channel.get(name, {})
                health_by_channel[name] = {
                    "source_id": source, "checked_at": stamp,
                    "status": "stale" if name in programmes_by_channel else "unavailable",
                    "programme_count": len((programmes_by_channel.get(name) or {}).get("programmes", [])),
                    "consecutive_failures": int(old.get("consecutive_failures", 0)) + 1,
                    "error": error,
                }

    return {
        "schema_version": 1,
        "generated_at": stamp,
        "timezone": "America/Sao_Paulo",
        "policy": {
            "priority": ["meuguia-br", "guia-de-tv-br"],
            "fallback": "preserve last known-good channel schedule on fetch or parse failure",
            "scope": "explicit channel-map mappings only",
        },
        "programmes": programmes_by_channel,
        "health": health_by_channel,
    }


def main() -> int:
    document = update_document()
    # Never publish a brand-new empty schedule document when every source failed.
    if not document["programmes"]:
        print("HTML EPG: no valid schedules available; no publication performed")
        return 0
    write_json_atomic(OUTPUT_FILE, document)
    statuses = {status: sum(1 for item in document["health"].values() if item.get("status") == status)
                for status in ("healthy", "stale", "unavailable")}
    print(f"HTML EPG: {len(document['programmes'])} channel schedules retained; health={statuses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
