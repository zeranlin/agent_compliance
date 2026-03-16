from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    generated_root: Path
    normalized_root: Path
    review_root: Path


def detect_paths() -> AppPaths:
    repo_root = Path(__file__).resolve().parents[2]
    generated_root = repo_root / "docs" / "generated"
    return AppPaths(
        repo_root=repo_root,
        generated_root=generated_root,
        normalized_root=generated_root / "normalized-documents",
        review_root=generated_root / "reviews",
    )
