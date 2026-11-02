#!/usr/bin/env python3
"""Read-only structural audit of channel logos, manifests and applied mappings."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = "catalog/channels/channels.json"
REFERENCE_FILE = "catalog/reference/saimo-channel-logos.json"
VARIANTS_FILE = "catalog/reference/reviewed-channel-logo-variants.json"


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def parse_logo_url(value: Any) -> tuple[str | None, str | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, None, "empty"
    raw = value.strip()
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return parsed.scheme.lower() or None, parsed.hostname, "invalid_url"
        if any(ord(char) < 32 for char in raw):
            return parsed.scheme.lower(), parsed.hostname, "invalid_url"
        return parsed.scheme.lower(), parsed.hostname.lower(), None
    except ValueError:
        return None, None, "invalid_url"


def _load_json(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def build_report(root: Path = ROOT) -> dict[str, Any]:
    catalog = _load_json(root, CHANNELS_FILE)
    reference_doc = _load_json(root, REFERENCE_FILE)
    variants_doc = _load_json(root, VARIANTS_FILE)
    channels = catalog.get("channels", []) if isinstance(catalog, dict) else []
    references = reference_doc.get("entries", []) if isinstance(reference_doc, dict) else []
    variants = variants_doc.get("reviewed_variants", []) if isinstance(variants_doc, dict) else []
    if not isinstance(channels, list) or not isinstance(references, list) or not isinstance(variants, list):
        raise ValueError("Logo audit inputs must contain channels, entries and reviewed_variants arrays")

    ids = Counter(str(item.get("id") or "") for item in channels if isinstance(item, dict) and item.get("id"))
    names = Counter(normalize_name(item.get("name")) for item in channels if isinstance(item, dict) and normalize_name(item.get("name")))
    reference_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reference_name_counts: Counter[str] = Counter()
    reference_invalid: list[dict[str, Any]] = []
    for item in references:
        if not isinstance(item, dict):
            reference_invalid.append({"reason": "entry_not_object"})
            continue
        key = normalize_name(item.get("name"))
        if key:
            reference_by_name[key].append(item)
            reference_name_counts[key] += 1
        scheme, host, error = parse_logo_url(item.get("logo_url"))
        if error or scheme != "https":
            reference_invalid.append({
                "name": str(item.get("name") or ""),
                "host": host,
                "scheme": scheme,
                "reason": error or "reference_not_https",
            })

    schemes: Counter[str] = Counter()
    hosts: Counter[str] = Counter()
    malformed: list[dict[str, str]] = []
    logo_to_channels: dict[str, list[dict[str, str]]] = defaultdict(list)
    missing: list[dict[str, str]] = []
    exact_matches = identical = different = missing_exact = ambiguous = 0
    differences: list[dict[str, str]] = []

    for channel in channels:
        if not isinstance(channel, dict):
            malformed.append({"id": "", "name": "", "reason": "channel_not_object"})
            continue
        channel_id = str(channel.get("id") or "")
        channel_name = str(channel.get("name") or "")
        logo = channel.get("logo_url")
        scheme, host, error = parse_logo_url(logo)
        if error == "empty":
            missing.append({"id": channel_id, "name": channel_name})
        elif error:
            malformed.append({"id": channel_id, "name": channel_name, "reason": error})
        else:
            schemes[scheme or "unknown"] += 1
            if host:
                hosts[host] += 1
            logo_to_channels[str(logo).strip()].append({"id": channel_id, "name": channel_name})

        key = normalize_name(channel_name)
        candidates = reference_by_name.get(key, []) if key else []
        if len(candidates) == 1:
            exact_matches += 1
            reference_url = str(candidates[0].get("logo_url") or "").strip()
            if logo and str(logo).strip() == reference_url:
                identical += 1
            elif logo:
                different += 1
                parsed_ref = urlsplit(reference_url)
                parsed_current = urlsplit(str(logo).strip())
                differences.append({
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "current_host": parsed_current.hostname or "",
                    "current_file": Path(parsed_current.path).name,
                    "reference_host": parsed_ref.hostname or "",
                    "reference_file": Path(parsed_ref.path).name,
                })
        elif len(candidates) > 1:
            ambiguous += 1
        elif not logo:
            missing_exact += 0

    for channel in missing:
        key = normalize_name(channel["name"])
        candidates = reference_by_name.get(key, []) if key else []
        if len(candidates) == 1:
            missing_exact += 1
        elif len(candidates) > 1:
            ambiguous += 1

    logo_groups = [
        {"logo_host": (urlsplit(url).hostname or ""), "logo_file": Path(urlsplit(url).path).name,
         "count": len(items), "channels": items[:20]}
        for url, items in logo_to_channels.items() if len(items) > 1
    ]
    logo_groups.sort(key=lambda item: (-item["count"], item["logo_host"], item["logo_file"]))

    variant_ids = Counter(str(item.get("channel_id") or "") for item in variants if isinstance(item, dict) and item.get("channel_id"))
    channel_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for channel in channels:
        if isinstance(channel, dict) and channel.get("id"):
            channel_by_id[str(channel["id"])].append(channel)
    variants_applied = variants_missing_logo = variants_invalid_id = 0
    for item in variants:
        if not isinstance(item, dict):
            variants_invalid_id += 1
            continue
        matches = channel_by_id.get(str(item.get("channel_id") or ""), [])
        if len(matches) != 1:
            variants_invalid_id += 1
        elif str(matches[0].get("logo_url") or "").strip():
            variants_applied += 1
        else:
            variants_missing_logo += 1

    return {
        "schema_version": 1,
        "report_type": "read_only_channel_logo_integrity_audit",
        "catalog_mutated": False,
        "live_image_probe_performed": False,
        "counts": {
            "channels_total": len(channels),
            "channels_with_logo": len(channels) - len(missing) - len(malformed),
            "channels_missing_logo": len(missing),
            "logo_urls_https": schemes["https"],
            "logo_urls_http": schemes["http"],
            "malformed_logo_urls": len(malformed),
            "duplicate_channel_ids": sum(1 for count in ids.values() if count > 1),
            "duplicate_normalized_channel_names": sum(1 for count in names.values() if count > 1),
            "unique_logo_urls": len(logo_to_channels),
            "shared_logo_url_groups": len(logo_groups),
            "channels_using_shared_logo_urls": sum(item["count"] for item in logo_groups),
            "manifest_entries": len(references),
            "manifest_unique_normalized_names": len(reference_name_counts),
            "manifest_duplicate_normalized_names": sum(1 for count in reference_name_counts.values() if count > 1),
            "manifest_invalid_or_non_https_urls": len(reference_invalid),
            "catalog_exact_name_reference_matches": exact_matches,
            "exact_name_matches_with_same_url": identical,
            "exact_name_matches_with_different_url": different,
            "missing_channels_with_exact_reference": missing_exact,
            "ambiguous_exact_name_reference_matches": ambiguous,
            "reviewed_variants": len(variants),
            "reviewed_variants_with_catalog_logo_applied": variants_applied,
            "reviewed_variants_still_missing_logo": variants_missing_logo,
            "reviewed_variants_with_missing_or_duplicate_channel_id": variants_invalid_id,
            "duplicate_variant_channel_ids": sum(1 for count in variant_ids.values() if count > 1),
        },
        "reference_url_differences_for_review": differences,
        "shared_logo_url_groups": logo_groups[:50],
        "missing_logo_channels_sample": missing[:50],
        "malformed_logo_channels": malformed,
        "invalid_manifest_entries": reference_invalid,
        "notes": [
            "A reference URL differing from an existing catalog URL is a review signal, not proof that the current logo is wrong.",
            "Shared logo URLs are reported for review only; regional and quality variants may legitimately share network branding.",
            "Only exact normalized-name matching is used. No fuzzy name matching or automatic replacement is performed.",
            "Manifest references are not counted as applied unless the catalog record contains a logo_url.",
            "HTTP/HTTPS and URL structure are checked locally; image availability, image content and visual brand correctness require a separate live/visual review.",
            "No stream, DRM, credentials, headers or playback fields are read or imported by this audit.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
