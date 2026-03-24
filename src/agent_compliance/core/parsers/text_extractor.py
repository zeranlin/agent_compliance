from __future__ import annotations

import subprocess
from pathlib import Path

PDF_TABLE_LABELS = (
    "是否采购节能产品",
    "是否采购环保产品",
    "是否采购进口产品",
    "未采购节能产品原因",
    "未采购环保产品原因",
    "未采购进口产品原因",
    "标的物所属行业",
    "合计金额（元）",
    "合计金额(元)",
    "单价（元）",
    "单价(元)",
)


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
        return _normalize_pdf_text(text)

    text = _extract_with_pdfplumber(source_path)
    if _looks_like_meaningful_text(text):
        return _normalize_pdf_text(text)

    return _normalize_pdf_text(_extract_with_textutil(source_path))


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


def _normalize_pdf_text(text: str) -> str:
    lines = [line.rstrip() for line in (text or "").splitlines()]
    normalized_lines: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        merged, consumed = _merge_pdf_table_label(lines, index)
        if merged is not None:
            normalized_lines.append(merged)
            index += consumed
            continue

        normalized_lines.append(line)
        index += 1
    return "\n".join(normalized_lines).strip()


def _merge_pdf_table_label(lines: list[str], start: int) -> tuple[str | None, int]:
    max_window = min(4, len(lines) - start)
    best_match: tuple[str, int] | None = None
    for size in range(1, max_window + 1):
        window = [lines[start + offset].strip() for offset in range(size)]
        if any(not part for part in window):
            break
        candidate = "".join(window)
        for label in PDF_TABLE_LABELS:
            if candidate == label:
                best_match = (label, size)
                break
            # Handle cases like "单价（元" + ")" and "合计金额" + "（元）"
            if label.startswith(candidate) and size < max_window:
                break
        if best_match is not None:
            return best_match
    return (None, 1)
