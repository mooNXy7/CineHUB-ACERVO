#!/usr/bin/env python3
"""Probe catalogo.txt channel candidates; HTTP success is not treated as playback proof."""
from __future__ import annotations

import argparse
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from .suggest_catalogo_channel_sources import safe_reference_stream
except ImportError:
    from suggest_catalogo_channel_sources import safe_reference_stream

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 8192
DEFAULT_TIMEOUT = 8
DEFAULT_WORKERS = 12


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        target = urljoin(request.full_url, new_url)
        ok, reason = safe_reference_stream(target)
        if not ok:
            raise ValueError(f"unsafe_redirect:{reason}")
        return super().redirect_request(request, file_pointer, code, message, headers, target)


def classify_payload(body: bytes, source_type: str) -> str:
    sample = body[:MAX_BODY].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if b"#extm3u" in sample[:4096]:
        return "hls_ok"
    if source_type == "dash" and (b"<mpd" in sample[:4096] or b"<?xml" in sample[:256]):
        return "dash_ok"
    if source_type == "hls":
        return "invalid_playlist"
    return "unknown_format"


def probe_one(candidate: dict, timeout: float = DEFAULT_TIMEOUT) -> dict:
    url = str(candidate.get("url") or "")
    ok, reason = safe_reference_stream(url)
    result = {
        "channel_id": candidate.get("channel_id"),
        "source_order": candidate.get("source_order"),
        "url": url,
        "host": candidate.get("host"),
        "source_type": candidate.get("source_type"),
        "probe_status": "unsafe",
        "http_status": None,
        "content_type": None,
        "bytes_read": 0,
        "elapsed_ms": None,
        "final_host": None,
        "error": None,
    }
    if not ok:
        result["error"] = reason
        return result
    headers = {
        "User-Agent": str((candidate.get("headers") or {}).get("user_agent") or
                          "CineHUB-ACERVO/0.2 channel-source-probe"),
        "Range": f"bytes=0-{MAX_BODY - 1}",
        "Accept": "application/vnd.apple.mpegurl, application/x-mpegURL, application/dash+xml, */*",
    }
    referer = str((candidate.get("headers") or {}).get("referer") or "")
    if referer:
        ref_ok, _ = safe_reference_stream(referer)
        if ref_ok:
            headers["Referer"] = referer
    request = Request(url, headers=headers, method="GET")
    started = time.monotonic()
    try:
        opener = build_opener(SafeRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_BODY)
            result["http_status"] = int(response.status)
            result["content_type"] = response.headers.get("Content-Type")
            result["bytes_read"] = len(body)
            final = urlsplit(response.geturl())
            result["final_host"] = final.hostname
            result["probe_status"] = classify_payload(body, str(candidate.get("source_type") or ""))
    except HTTPError as exc:
        result["http_status"] = int(exc.code)
        result["content_type"] = exc.headers.get("Content-Type") if exc.headers else None
        result["probe_status"] = "http_error"
        result["error"] = f"http_{exc.code}"
    except (TimeoutError, socket.timeout):
        result["probe_status"] = "timeout"
        result["error"] = "timeout"
    except ValueError as exc:
        result["probe_status"] = "unsafe_redirect"
        result["error"] = str(exc)[:160]
    except (URLError, OSError) as exc:
        result["probe_status"] = "network_error"
        result["error"] = type(exc).__name__
    finally:
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return result


def build_report(input_path: Path, output_path: Path, workers: int = DEFAULT_WORKERS,
                 timeout: float = DEFAULT_TIMEOUT) -> dict:
    source_report = json.loads(input_path.read_text(encoding="utf-8"))
    candidates = [
        {**source, "channel_id": channel.get("channel_id")}
        for channel in source_report.get("candidates", [])
        for source in channel.get("sources", [])
    ]
    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), 24))) as pool:
        futures = [pool.submit(probe_one, item, timeout) for item in candidates]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (str(item.get("channel_id")), int(item.get("source_order") or 0)))
    statuses = {}
    for item in results:
        status = item["probe_status"]
        statuses[status] = statuses.get(status, 0) + 1
    report = {
        "schema_version": 1,
        "report_type": "catalogo_channel_source_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_mutated": False,
        "probes": len(results),
        "counts": statuses,
        "policy": [
            "Only HTTPS candidates from the read-only exact-name report are probed.",
            "Requests are limited to 8 KiB and use a Range header.",
            "Only User-Agent and safe HTTPS Referer may be sent; no authorization or cookies.",
            "Redirects are re-checked for HTTPS and URL safety.",
            "HLS playlist syntax is a reachability signal, not proof of playback on a TV device.",
            "Only hls_ok results may be considered by the separate guarded application step.",
        ],
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "reports/catalogo-channel-source-candidates.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/catalogo-channel-source-health.json")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()
    report = build_report(args.input, args.output, args.workers, args.timeout)
    print(json.dumps({"probes": report["probes"], "counts": report["counts"],
                      "catalog_mutated": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
