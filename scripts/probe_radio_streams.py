#!/usr/bin/env python3
"""Read-only, audio-aware health checks for CineHUB radio stream URLs."""
from __future__ import annotations
import argparse, json, socket, ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

try:
    from .update_catalog import ROOT, SafeRedirectHandler, safe_https_url
except ImportError:
    from update_catalog import ROOT, SafeRedirectHandler, safe_https_url

AUDIO_MIME_TYPES = {
    "application/ogg", "application/vnd.apple.mpegurl", "application/x-mpegurl",
    "audio/aac", "audio/aacp", "audio/flac", "audio/mp4", "audio/mpeg",
    "audio/ogg", "audio/wav", "audio/webm", "audio/x-aac", "audio/x-mpeg",
}
TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


def classify_payload(content_type: str, sample: bytes) -> tuple[str, str]:
    """Classify payload evidence; an HTTP 200 response alone is insufficient."""
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    data = (sample or b"")[:4096]
    lowered = data.lstrip().lower()
    if not data:
        return "unverified", "empty_response"
    if lowered.startswith((b"<!doctype html", b"<html", b"<head", b"<body")) or mime == "text/html":
        return "non_audio", "html_response"
    if data.lstrip().startswith(b"#EXTM3U"):
        playlist = data.upper()
        if any(tag in playlist for tag in (b"#EXTINF", b"#EXT-X-STREAM-INF", b"#EXT-X-TARGETDURATION")):
            return "functional", "hls_playlist"
        return "unverified", "incomplete_hls_playlist"
    if mime.startswith("audio/") or mime in AUDIO_MIME_TYPES:
        return "functional", "audio_content_type"
    if (
        data.startswith(b"ID3")
        or data.startswith(b"OggS")
        or data.startswith(b"fLaC")
        or (data.startswith(b"RIFF") and b"WAVE" in data[:16])
        or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    ):
        return "functional", "audio_signature"
    return "unverified", "unsupported_content_type_or_signature"


def classify_http_error(status: int) -> tuple[str, str]:
    if status in TRANSIENT_HTTP_CODES:
        return "temporarily_unavailable", f"http_{status}_transient"
    if status in {404, 410}:
        return "permanently_unavailable", f"http_{status}_not_found"
    return "unverified", f"http_{status}"


def host_only(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def probe_radio(radio: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    url = str(radio.get("stream_url") or "").strip()
    result = {
        "id": str(radio.get("id") or ""),
        "name": str(radio.get("name") or ""),
        "status": "unverified",
        "detail": "not_probed",
        "http_status": None,
        "content_type": None,
        "host": host_only(url),
    }
    if not safe_https_url(url):
        result.update(status="invalid_url", detail="https_url_required")
        return result
    request = Request(url, headers={
        "User-Agent": "CineHUB-ACERVO-RadioProbe/1.0",
        "Accept": "audio/*,application/ogg,application/vnd.apple.mpegurl,application/x-mpegURL,*/*;q=0.2",
        "Range": "bytes=0-4095",
        "Icy-MetaData": "0",
    })
    try:
        with build_opener(SafeRedirectHandler()).open(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            content_type = str(response.headers.get("Content-Type", ""))
            classification, detail = classify_payload(content_type, response.read(4096))
            result.update(
                status=classification,
                detail=detail,
                http_status=status,
                content_type=content_type.split(";", 1)[0].strip().lower() or None,
                host=host_only(response.geturl()) or result["host"],
            )
            if not 200 <= status < 300 and classification == "functional":
                result.update(status="unverified", detail=f"http_{status}_unexpected")
    except HTTPError as exc:
        classification, detail = classify_http_error(int(exc.code))
        result.update(status=classification, detail=detail, http_status=int(exc.code))
    except ssl.SSLError:
        result.update(status="unverified", detail="tls_validation_error")
    except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError):
        result.update(status="temporarily_unavailable", detail="network_or_timeout_error")
    except Exception as exc:
        result.update(status="unverified", detail=f"probe_error_{type(exc).__name__}")
    return result


def build_report(root: Path = ROOT, timeout: float = 8.0, workers: int = 16) -> dict[str, Any]:
    document = json.loads((root / "catalog/radios/radios.json").read_text(encoding="utf-8"))
    radios = [item for item in document.get("radios", []) if isinstance(item, dict)]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        results = list(executor.map(lambda item: probe_radio(item, timeout), radios))
    statuses = (
        "functional", "temporarily_unavailable", "permanently_unavailable",
        "non_audio", "unverified", "invalid_url",
    )
    counts = {status: sum(item["status"] == status for item in results) for status in statuses}
    return {
        "schema_version": 1,
        "report_type": "radio_stream_audio_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "catalog_mutated": False,
        "total_radios": len(radios),
        "counts": counts,
        "method": "HTTPS GET with bounded Range read; validates audio MIME, known audio signatures or HLS playlist markers; HTTP success alone is not accepted.",
        "limitations": [
            "A successful probe confirms an audio-like response or HLS playlist at probe time, not uninterrupted playback or every codec/device combination.",
            "Temporary network failures are not treated as permanent station failures and never remove catalog records.",
            "Only hostnames are recorded; stream query strings and credentials are not copied into the report.",
        ],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--output", type=Path, default=Path("reports/radio-stream-health.json"))
    args = parser.parse_args()
    report = build_report(args.root, timeout=args.timeout, workers=args.workers)
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "total_radios": report["total_radios"],
        "counts": report["counts"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
