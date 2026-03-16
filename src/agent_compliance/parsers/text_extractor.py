from __future__ import annotations

import subprocess
from pathlib import Path


def extract_text(source_path: Path) -> str:
    suffix = source_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return source_path.read_text(encoding="utf-8")

    if suffix in {".docx", ".doc", ".rtf", ".pdf"}:
        return _extract_with_textutil(source_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_with_textutil(source_path: Path) -> str:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(source_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout
