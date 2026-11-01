#!/usr/bin/env python3
"""Refresh radio stream references from an authorized pipe-delimited source."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .update_catalog import ROOT, SOURCES, fetch, safe_https_url, safe_source_url, atomic_write_json, normalize_key
except ImportError:
    from update_catalog import ROOT, SOURCES, fetch, safe_https_url, safe_source_url, atomic_write_json, normalize_key

OUT = ROOT / "catalog/radios/radios.json"
MAX_SOURCE_RECORDS = 5000


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "radio"


def parse_radio_source(text: str, source_id: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    counts = {"lines_seen": 0, "accepted": 0, "malformed": 0, "unsafe_streams": 0}
    seen: set[tuple[str, str]] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        counts["lines_seen"] += 1
        if "|" not in line:
            counts["malformed"] += 1
            continue
        name, stream_url = (part.strip() for part in line.split("|", 1))
        if not name or not stream_url:
            counts["malformed"] += 1
            continue
        if not safe_https_url(stream_url):
            counts["unsafe_streams"] += 1
            continue
        key = (normalize_key(name), stream_url)
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "id": "radio." + slug(name),
            "name": name,
            "stream_url": stream_url,
            "logo_url": None,
            "genre": None,
            "source_id": source_id,
        })
        counts["accepted"] += 1
        if len(records) > MAX_SOURCE_RECORDS:
            raise ValueError(f"radio source exceeds {MAX_SOURCE_RECORDS} records")
    return records, counts


def merge_radio_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = [dict(item) for item in existing if isinstance(item, dict)]
    by_id: dict[str, list[dict[str, Any]]] = {}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in result:
        if item.get("id"):
            by_id.setdefault(str(item["id"]), []).append(item)
        if item.get("name"):
            by_name.setdefault(normalize_key(item["name"]), []).append(item)

    added = filled_stream = unchanged = conflicts = ambiguous = 0
    conflict_names: list[str] = []
    for item in incoming:
        id_matches = by_id.get(str(item.get("id") or ""), [])
        name_matches = by_name.get(normalize_key(item.get("name")), [])
        matches = id_matches or name_matches
        if len(matches) > 1:
            ambiguous += 1
            continue
        if not matches:
            clone = dict(item)
            result.append(clone)
            by_id.setdefault(str(clone.get("id")), []).append(clone)
            by_name.setdefault(normalize_key(clone.get("name")), []).append(clone)
            added += 1
            continue

        target = matches[0]
        current_url = str(target.get("stream_url") or "").strip()
        candidate_url = str(item.get("stream_url") or "").strip()
        if not current_url and candidate_url:
            target["stream_url"] = candidate_url
            if not target.get("source_id"):
                target["source_id"] = item.get("source_id")
            filled_stream += 1
        elif current_url == candidate_url:
            unchanged += 1
        elif current_url and candidate_url:
            conflicts += 1
            if len(conflict_names) < 100:
                conflict_names.append(str(target.get("name") or item.get("name") or ""))

        # Only fill missing descriptive fields. Never overwrite existing logos/genres.
        for field in ("logo_url", "genre"):
            if not target.get(field) and item.get(field):
                target[field] = item[field]

    return result, {
        "added": added,
        "filled_stream": filled_stream,
        "unchanged": unchanged,
        "stream_conflicts": conflicts,
        "ambiguous_matches": ambiguous,
        "stream_conflict_names": conflict_names,
    }


def update(root: Path = ROOT) -> dict[str, Any]:
    sources_path = root / "sources/sources.json"
    out_path = root / "catalog/radios/radios.json"
    cfg = json.loads(sources_path.read_text(encoding="utf-8"))
    current = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {
        "schema_version": 1, "radios": []
    }
    if not isinstance(current, dict) or not isinstance(current.get("radios"), list):
        raise ValueError("catalog/radios/radios.json must contain a radios array")

    active = [s for s in cfg.get("sources", [])
              if isinstance(s, dict) and s.get("enabled") and s.get("category") == "radio"]
    collected: list[dict[str, Any]] = []
    failures: list[str] = []
    source_counts: list[dict[str, Any]] = []
    for source in sorted(active, key=lambda item: item.get("priority", 999)):
        source_id = str(source.get("id") or "")
        url = str(source.get("url") or "")
        if source.get("format") != "pipe-delimited":
            failures.append(f"{source_id or '?'}: formato não suportado")
            continue
        if not safe_source_url(url):
            failures.append(f"{source_id or '?'}: URL HTTPS ausente/inválida")
            continue
        try:
            parsed, counts = parse_radio_source(fetch(url), source_id)
            if not parsed:
                raise ValueError("nenhuma rádio com nome e stream HTTPS seguro")
            source_counts.append({"source_id": source_id, **counts})
            collected.extend(parsed)
        except Exception as exc:
            failures.append(f"{source_id or '?'}: {type(exc).__name__}: {exc}")

    if active and failures and not collected:
        raise RuntimeError("Nenhuma fonte de rádio segura válida; catálogo anterior preservado: " + "; ".join(failures))
    if collected:
        original_radios = list(current["radios"])
        merged, merge_counts = merge_radio_records(original_radios, collected)
        catalog_mutated = merged != original_radios
        if catalog_mutated:
            current["radios"] = merged
            current["generated_at"] = datetime.now(timezone.utc).isoformat()
            atomic_write_json(out_path, current)
    else:
        merged = current["radios"]
        catalog_mutated = False
        merge_counts = {"added": 0, "filled_stream": 0, "unchanged": 0,
                        "stream_conflicts": 0, "ambiguous_matches": 0,
                        "stream_conflict_names": []}

    report = {
        "schema_version": 1,
        "report_type": "radio_source_refresh",
        "catalog_mutated": catalog_mutated,
        "active_sources": len(active),
        "sources": source_counts,
        "merge": merge_counts,
        "failures": failures,
        "safety": [
            "Only name and HTTPS stream fields are read from the authorized reference.",
            "Existing non-empty streams, logos, genres, and IDs are never overwritten.",
            "Conflicting streams are reported for review and are not substituted.",
            "No DRM, headers, credentials, or playback controls are imported.",
        ],
    }
    report_path = root / "reports/radio-source-refresh.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "failures"}, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    update(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
