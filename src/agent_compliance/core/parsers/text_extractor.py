from __future__ import annotations

import subprocess
from pathlib import Path


def extract_text(source_path: Path) -> str:
    suffix = source_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return source_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        return _extract_pdf_text(source_path)

    if suffix in {".docx", ".doc", ".rtf"}:
        return _extract_with_textutil(source_path)

    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf_text(source_path: Path) -> str:
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    text = _extract_with_pypdf(source_path)
    if _looks_like_meaningful_text(text):
        return text

    text = _extract_with_pdfplumber(source_path)
    if _looks_like_meaningful_text(text):
        return text

    return _extract_with_textutil(source_path)


def _extract_with_textutil(source_path: Path) -> str:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(source_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _extract_with_pypdf(source_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(str(source_path))
    except Exception:
        return ""

    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(part for part in parts if part).strip()


def _extract_with_pdfplumber(source_path: Path) -> str:
    try:
        import pdfplumber
    except Exception:
        return ""

    try:
        with pdfplumber.open(source_path) as pdf:
            parts = [(page.extract_text() or "") for page in pdf.pages]
    except Exception:
        return ""
    return "\n".join(part for part in parts if part).strip()


def _looks_like_meaningful_text(text: str) -> bool:
    normalized = " ".join((text or "").split()).strip()
    return len(normalized) >= 20
