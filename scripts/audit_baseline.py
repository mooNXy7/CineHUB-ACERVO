#!/usr/bin/env python3
"""Read-only inventory and integrity report for the ACERVO V2 baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github/workflows"
SCRIPT_REF = re.compile(r"(scripts/[A-Za-z0-9_./-]+\.py)")
CLONE_REF = re.compile(r"git clone[^\n]*?https?://[^\s]+", re.I)
IMAGE_SUFFIX = re.compile(r"\.(?:png|jpe?g|webp|gif|svg|ico|avif)$", re.I)


def read_json(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def radio_inventory(path: Path) -> dict:
    data = read_json(path)
    rows = data.get("radios", []) if isinstance(data, dict) else []
    fields = ("id", "name", "stream_url", "logo_url", "genre", "source_id")
    missing = {
        field: sum(row.get(field) in (None, "") for row in rows if isinstance(row, dict))
        for field in fields
    }
    ids = [row.get("id") for row in rows if isinstance(row, dict) and row.get("id")]
    image_streams = []
    non_https_logos = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        stream = str(row.get("stream_url") or "")
        if IMAGE_SUFFIX.search(urlsplit(stream).path):
            image_streams.append(row.get("id") or row.get("name"))
        logo = str(row.get("logo_url") or "")
        if logo and not logo.lower().startswith("https://"):
            non_https_logos += 1
    return {
        "records": len(rows),
        "missing_fields": missing,
        "duplicate_ids": len(ids) - len(set(ids)),
        "probable_image_urls_in_stream": len(image_streams),
        "image_stream_examples": image_streams[:10],
        "non_https_logo_urls": non_https_logos,
    }


def directory_inventory() -> dict:
    requested = ("catalog", "sources", "normalizer", "scripts", "tests", "reports", ".github/workflows")
    inventory = {}
    for name in requested:
        folder = ROOT / name
        files = sorted(path for path in folder.rglob("*") if path.is_file()) if folder.exists() else []
        inventory[name] = {
            "exists": folder.is_dir(),
            "file_count": len(files),
            "total_bytes": sum(path.stat().st_size for path in files),
            "examples": [path.relative_to(ROOT).as_posix() for path in files[:40]],
        }
    return inventory


def snapshot_catalogs() -> dict:
    entries = []
    for name in ("catalog", "sources"):
        folder = ROOT / name
        if not folder.exists():
            continue
        for path in sorted(item for item in folder.rglob("*") if item.is_file()):
            payload = path.read_bytes()
            entries.append({
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
    canonical = "\\n".join(str(item["sha256"]) + "  " + str(item["path"]) for item in entries)
    return {
        "file_count": len(entries),
        "aggregate_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": entries,
    }


def configuration_inventory() -> list:
    candidates = (
        "pyproject.toml", "requirements.txt", "requirements-dev.txt", "Pipfile",
        "Pipfile.lock", "poetry.lock", "uv.lock", "setup.cfg", "tox.ini",
        "Makefile", "package.json", "package-lock.json", ".python-version",
    )
    return [
        {"path": name, "bytes": (ROOT / name).stat().st_size}
        for name in candidates if (ROOT / name).is_file()
    ]

def build_report() -> dict:
    workflows = []
    external_clones = []
    if WORKFLOW_DIR.exists():
        paths = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
        for path in paths:
            content = path.read_text(encoding="utf-8")
            scripts = sorted(set(SCRIPT_REF.findall(content)))
            missing = [item for item in scripts if not (ROOT / item).is_file()]
            workflows.append({
                "path": path.relative_to(ROOT).as_posix(),
                "script_references": scripts,
                "missing_scripts": missing,
                "push_branch_filters": re.findall(r"branches:\s*\[([^]]+)\]", content),
            })
            external_clones.extend(CLONE_REF.findall(content))

    vod = read_json(ROOT / "catalog/vod/index.json")
    categories = {}
    for name, info in (vod.get("categories") or {}).items():
        index_path = info.get("index_path") if isinstance(info, dict) else None
        full_path = ROOT / index_path if index_path else None
        actual_count = None
        if full_path and full_path.is_file():
            try:
                payload = read_json(full_path)
                actual_count = len(payload) if isinstance(payload, list) else None
            except (OSError, json.JSONDecodeError):
                actual_count = None
        categories[name] = {
            "declared_count": info.get("count") if isinstance(info, dict) else None,
            "index_path": index_path,
            "index_exists": bool(full_path and full_path.is_file()),
            "actual_count": actual_count,
            "count_matches": actual_count == info.get("count") if actual_count is not None and isinstance(info, dict) else None,
        }

    epg = read_json(ROOT / "catalog/epg/sources.json")
    sources = read_json(ROOT / "sources/sources.json")
    logo_root = ROOT / "catalog/logos"
    logo_files = [p.relative_to(ROOT).as_posix() for p in logo_root.rglob("*") if p.is_file()] if logo_root.exists() else []
    channels = read_json(ROOT / "catalog/channels/channels.json")
    channel_rows = channels.get("channels", []) if isinstance(channels, dict) else []
    workflow_text = "\n".join(p.read_text(encoding="utf-8") for p in WORKFLOW_DIR.glob("*.y*ml"))
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head or None,
        "repository_layout": directory_inventory(),
        "configuration_files": configuration_inventory(),
        "catalog_snapshot": snapshot_catalogs(),
        "scope": "read-only; no catalog mutation or network probes",
        "inventory": {
            "channels": {"records": len(channel_rows), "path": "catalog/channels/channels.json"},
            "radios": radio_inventory(ROOT / "catalog/radios/radios.json"),
            "vod": {"manifest_path": "catalog/vod/index.json", "categories": categories},
            "epg": {"sources": len(epg.get("sources", [])), "channel_map_exists": (ROOT / "catalog/epg/channel-map.json").is_file()},
            "sources_registry": {"sources": len(sources.get("sources", []))},
            "logos": {"files": len(logo_files), "examples": logo_files[:20]},
        },
        "workflows": workflows,
        "missing_workflow_scripts": sorted({item for workflow in workflows for item in workflow["missing_scripts"]}),
        "external_clone_dependencies": sorted(set(external_clones)),
        "tmdb": {
            "supabase_function_references": workflow_text.count("supabase.co/functions/"),
            "tmdb_token_secret_names_in_workflows": sorted(set(re.findall(
                r"secrets\.([A-Z0-9_]*TMDB[A-Z0-9_]*)", workflow_text
            ))),
            "note": "Repository references only; Supabase secret values are not inspected.",
        },
    }


def render_markdown(report: dict) -> str:
    inventory = report["inventory"]
    radios = inventory["radios"]
    lines = [
        "# ACERVO V2 — Baseline técnico",
        "",
        f"- Gerado em: {report['generated_at']}",
        f"- Escopo: {report['scope']}",
        "",
        "## Inventário",
        "",
        f"- Canais: {inventory['channels']['records']} registros",
        f"- Rádios: {radios['records']} registros",
        f"- VOD: " + ", ".join(
            f"{name}={info['declared_count']} (arquivo {'presente' if info['index_exists'] else 'ausente'}, contagem real={info['actual_count']})"
            for name, info in inventory["vod"]["categories"].items()
        ),
        f"- EPG: {inventory['epg']['sources']} fontes",
        f"- Registry de fontes: {inventory['sources_registry']['sources']} entradas",
        f"- Logos: {inventory['logos']['files']} arquivos locais",
        "",
        "## Qualidade de rádios",
        "",
        f"- Campos ausentes: {json.dumps(radios['missing_fields'], ensure_ascii=False)}",
        f"- IDs duplicados: {radios['duplicate_ids']}",
        f"- URLs com extensão de imagem no campo stream_url: {radios['probable_image_urls_in_stream']}",
        f"- Logos fora de HTTPS: {radios['non_https_logo_urls']}",
        "",
        "## Workflows",
        "",
    ]
    for workflow in report["workflows"]:
        lines.append(f"- {workflow['path']}: scripts={len(workflow['script_references'])}, ausentes={workflow['missing_scripts']}")
    lines += [
        "",
        "## Dependências externas",
        "",
        *[f"- {item}" for item in report["external_clone_dependencies"]],
        "",
        "## TMDB",
        "",
        f"- Referências a funções Supabase em workflows: {report['tmdb']['supabase_function_references']}",
        f"- Segredos TMDB declarados em workflows: {report['tmdb']['tmdb_token_secret_names_in_workflows']}",
        f"- {report['tmdb']['note']}",
        "",
        "## Política",
        "",
        "Relatório somente de leitura. Nenhum catálogo foi modificado, removido ou publicado.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/baseline")
    args = parser.parse_args()
    report = build_report()
    output = ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    (output / "baseline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "baseline.md").write_text(render_markdown(report), encoding="utf-8")
    snapshot_lines = [item["sha256"] + "  " + item["path"] for item in report["catalog_snapshot"]["files"]]
    (output / "catalog-snapshot.sha256").write_text("\\n".join(snapshot_lines) + "\\n", encoding="utf-8")
    print(render_markdown(report))
    if report["missing_workflow_scripts"]:
        print("Missing workflow scripts: " + ", ".join(report["missing_workflow_scripts"]))


if __name__ == "__main__":
    main()
