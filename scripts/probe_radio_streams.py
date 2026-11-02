#!/usr/bin/env python3
"""Audio-aware health checks and safe fallback promotion for CineHUB radio sources."""
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
        if any(tag in playlist for tag in (
            b"#EXT-X-STREAM-INF", b"#EXT-X-TARGETDURATION",
            b"#EXT-X-MEDIA-SEQUENCE", b"#EXT-X-ENDLIST",
        )):
            return "functional", "hls_playlist"
        if b"#EXTINF" in playlist:
            return "unverified", "m3u_playlist_requires_target_audio_validation"
        return "unverified", "incomplete_hls_playlist"
    if mime in {"audio/x-scpls", "audio/x-mpegurl"} or lowered.startswith(b"[playlist]"):
        return "unverified", "playlist_requires_target_audio_validation"
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



def apply_alternative_probe_results(
    radios: list[dict[str, Any]],
    primary_results: list[dict[str, Any]],
    alternative_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """Update alternative health and promote only verified audio after definitive primary failure."""
    by_id = {str(radio.get("id") or ""): radio for radio in radios}
    primary_by_id = {str(result.get("id") or ""): dict(result) for result in primary_results}
    alternatives_by_id: dict[str, list[dict[str, Any]]] = {}
    mutated = False

    for result in alternative_results:
        radio_id = str(result.get("id") or "")
        radio = by_id.get(radio_id)
        source_index = result.get("source_index")
        sources = radio.get("sources") if radio else None
        if not isinstance(sources, list) or not isinstance(source_index, int):
            continue
        if source_index < 0 or source_index >= len(sources):
            continue
        source = sources[source_index]
        if not isinstance(source, dict):
            continue
        if source.get("status") != result.get("status"):
            source["status"] = result.get("status")
            mutated = True
        alternatives_by_id.setdefault(radio_id, []).append(result)

    promotions: list[dict[str, Any]] = []
    promotable_primary_statuses = {
        "permanently_unavailable", "non_audio", "invalid_url",
    }
    for radio_id, radio in by_id.items():
        primary = primary_by_id.get(radio_id)
        if not primary or primary.get("status") not in promotable_primary_statuses:
            continue
        sources = radio.get("sources")
        if not isinstance(sources, list) or not sources:
            continue
        functional_alternatives = [
            item for item in alternatives_by_id.get(radio_id, [])
            if item.get("status") == "functional" and item.get("url")
        ]
        if not functional_alternatives:
            continue
        functional_alternatives.sort(
            key=lambda item: int(item.get("priority") or 0), reverse=True
        )
        chosen = functional_alternatives[0]
        new_url = str(chosen["url"])
        old_url = str(radio.get("stream_url") or "")
        if not new_url or new_url == old_url:
            continue

        old_status = str(primary.get("status") or "unverified")
        old_source_id = str(radio.get("source_id") or "previous-primary")
        previous_entry = next(
            (item for item in sources if isinstance(item, dict) and str(item.get("url") or "") == old_url),
            None,
        )
        if previous_entry:
            previous_entry["status"] = old_status
        elif old_url:
            sources.append({
                "url": old_url,
                "priority": 10,
                "source_id": old_source_id,
                "status": old_status,
            })

        radio["sources"] = [
            item for item in sources
            if not (
                isinstance(item, dict)
                and str(item.get("url") or "") == new_url
            )
        ]
        radio["stream_url"] = new_url
        promoted_source_id = str(chosen.get("source_id") or "validated-alternative")
        radio["source_id"] = promoted_source_id
        promotions.append({
            "radio_id": radio_id,
            "radio_name": str(radio.get("name") or ""),
            "previous_primary_status": old_status,
            "new_source_id": promoted_source_id,
            "new_primary_host": str(chosen.get("host") or ""),
        })
        primary_by_id[radio_id] = {
            "id": radio_id,
            "name": str(radio.get("name") or ""),
            "status": "functional",
            "detail": str(chosen.get("detail") or "verified_alternative_audio"),
            "http_status": chosen.get("http_status"),
            "content_type": chosen.get("content_type"),
            "host": str(chosen.get("host") or ""),
            "recovered_from": old_status,
            "recovered_source_id": promoted_source_id,
        }
        mutated = True

    final_primary_results = [
        primary_by_id.get(str(result.get("id") or ""), result)
        for result in primary_results
    ]
    return final_primary_results, promotions, mutated


def probe_alternative_source(
    radio: dict[str, Any], source: dict[str, Any], source_index: int, timeout: float
) -> dict[str, Any]:
    result = probe_radio({
        "id": str(radio.get("id") or ""),
        "name": str(radio.get("name") or ""),
        "stream_url": str(source.get("url") or ""),
    }, timeout)
    result.update(
        source_id=str(source.get("source_id") or "alternative"),
        priority=int(source.get("priority") or 0),
        source_index=source_index,
        url=str(source.get("url") or ""),
    )
    return result


def build_report(root: Path = ROOT, timeout: float = 8.0, workers: int = 16) -> dict[str, Any]:
    document = json.loads((root / "catalog/radios/radios.json").read_text(encoding="utf-8"))
    radios = [item for item in document.get("radios", []) if isinstance(item, dict)]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        primary_results = list(executor.map(lambda item: probe_radio(item, timeout), radios))

    alternative_tasks = [
        (radio, index, source)
        for radio in radios
        for index, source in enumerate(radio.get("sources", []) if isinstance(radio.get("sources"), list) else [])
        if isinstance(source, dict) and source.get("url")
    ]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        alternative_results = list(executor.map(
            lambda task: probe_alternative_source(task[0], task[2], task[1], timeout),
            alternative_tasks,
        ))

    primary_statuses = (
        "functional", "temporarily_unavailable", "permanently_unavailable",
        "non_audio", "unverified", "invalid_url",
    )
    pre_promotion_counts = {
        status: sum(item["status"] == status for item in primary_results)
        for status in primary_statuses
    }
    results, promotions, catalog_mutated = apply_alternative_probe_results(
        radios, primary_results, alternative_results
    )
    counts = {
        status: sum(item["status"] == status for item in results)
        for status in primary_statuses
    }
    alternative_counts = {
        status: sum(item["status"] == status for item in alternative_results)
        for status in primary_statuses
    }

    if catalog_mutated:
        document["radios"] = radios
        (root / "catalog/radios/radios.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    public_alternative_results = [
        {
            "radio_id": item["id"],
            "radio_name": item["name"],
            "source_id": item["source_id"],
            "priority": item["priority"],
            "status": item["status"],
            "detail": item["detail"],
            "http_status": item["http_status"],
            "content_type": item["content_type"],
            "host": item["host"],
        }
        for item in alternative_results
    ]
    return {
        "schema_version": 1,
        "report_type": "radio_stream_audio_probe",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_mutated": catalog_mutated,
        "total_radios": len(radios),
        "counts": counts,
        "pre_promotion_counts": pre_promotion_counts,
        "alternative_sources_tested": len(alternative_results),
        "alternative_source_counts": alternative_counts,
        "promotions": promotions,
        "method": "HTTPS GET with bounded Range read; validates audio MIME, known audio signatures or HLS playlist markers; promotes an alternative only when it is audio-verified and the primary is permanently unavailable, invalid or non-audio.",
        "limitations": [
            "A successful probe confirms an audio-like response or HLS playlist at probe time, not uninterrupted playback or every codec/device combination.",
            "Temporary network failures and unverified responses never trigger primary replacement; all catalog records are preserved.",
            "Only hostnames are recorded in reports; stream query strings and credentials are not copied into the report.",
        ],
        "results": results,
        "alternative_results": public_alternative_results,
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
        "alternative_sources_tested": report["alternative_sources_tested"],
        "promotions": len(report["promotions"]),
        "catalog_mutated": report["catalog_mutated"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
