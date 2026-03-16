from __future__ import annotations

from pathlib import Path

from agent_compliance.config import detect_paths


def list_reference_files() -> list[str]:
    paths = detect_paths()
    reference_root = paths.repo_root / "docs" / "references"
    return sorted(str(path.relative_to(paths.repo_root)) for path in reference_root.rglob("*.md"))


def index_exists() -> bool:
    paths = detect_paths()
    return (paths.repo_root / "docs" / "references" / "reference-index.md").exists()
