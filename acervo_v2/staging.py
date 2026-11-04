from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def overlay_path(base_root: Path, staging_root: Path, source_path: Path) -> Path:
    base = base_root.resolve()
    relative = source_path.resolve().relative_to(base)
    return staging_root.resolve() / relative


def finalize_overlay(base_root: Path, staging_root: Path, targets: list[Path], metadata: dict) -> dict:
    base = base_root.resolve()
    staging = staging_root.resolve()
    entries = []
    for target in sorted({p.resolve() for p in targets}, key=lambda p: p.as_posix()):
        relative = target.relative_to(staging).as_posix()
        original = base / relative
        entries.append({
            "path": relative,
            "base_sha256": hashlib.sha256(original.read_bytes()).hexdigest() if original.exists() else None,
            "candidate_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size,
        })
    manifest = {
        "schema_version": 1,
        "candidate_type": "vod-catalog-overlay",
        "base_ref": os.environ.get("GITHUB_SHA"),
        "catalog_mutated": False,
        "files": entries,
        "metadata": metadata,
    }
    atomic_json(staging / "candidate-manifest.json", manifest)
    return manifest
