from __future__ import annotations

from html import escape as html_escape
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from agent_compliance.agents.compliance_review.pipeline import ComplianceReviewRunResult, run_pipeline
from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import route_procurement_stage
from agent_compliance.apps.web.review.jobs import mark_review_job
from agent_compliance.core.config import LLMConfig, detect_llm_config, detect_paths
from agent_compliance.core.knowledge.procurement_catalog import classify_procurement_catalog
from agent_compliance.core.parsers.pagination import page_hint_for_line
from agent_compliance.core.schemas import NormalizedDocument, ReviewResult


def persist_upload(filename: str, content: bytes) -> Path:
    paths = detect_paths()
    paths.uploads_root.mkdir(parents=True, exist_ok=True)
    target = paths.uploads_root / Path(filename).name
    target.write_bytes(content)
    return target


def build_download_content_disposition(filename: str) -> str:
    ascii_name = "".join(ch if ord(ch) < 128 else "_" for ch in filename)
    if not ascii_name.strip("._"):
        ascii_name = "review-export"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"


def web_llm_config(use_llm: bool) -> LLMConfig:
    config = detect_llm_config()
    return LLMConfig(
        enabled=bool(use_llm or config.enabled),
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )


def flag_value(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "on", "yes"}


def run_review_sync(
    source_path: Path,
    *,
    use_cache: bool,
    use_llm: bool,
    parser_mode: str,
) -> ComplianceReviewRunResult:
    return run_pipeline(
        source_path,
        use_cache=use_cache,
        refresh_cache=False,
        llm_config=web_llm_config(use_llm),
        parser_mode=parser_mode,
        output_stem=None,
        write_outputs=True,
    )


def run_review_job(
    job_id: str,
    source_path: Path,
    *,
    use_cache: bool,
    use_llm: bool,
    parser_mode: str,
) -> None:
    mark_review_job(
        job_id,
        status="running",
        current_step="parse",
        run_steps=("parse",),
        message="正在解析文档、提取正文、章节和表格内容。",
    )
    try:
        mark_review_job(
            job_id,
            current_step="base_scan",
            complete_steps=("parse", "catalog"),
            run_steps=("base_scan", "rule_scan"),
            message="正在扫描基础条款，识别资格、评分、技术、商务/验收风险。",
        )
        review_run = run_review_sync(
            source_path,
            use_cache=use_cache,
            use_llm=use_llm,
            parser_mode=parser_mode,
        )
        if review_run.llm_config.enabled:
            llm_completed_steps = ("llm_enhance", "llm_document_audit", "llm_chapter_summary", "llm_legal_reasoning")
        else:
            llm_completed_steps = ()
        payload = build_review_web_payload(review_run)
        mark_review_job(
            job_id,
            status="completed",
            current_step="done",
            complete_steps=("base_scan", "rule_scan", "scoring", "mixed_scope", "commercial", "finalize", "arbiter", "evidence", "done", *llm_completed_steps),
            skip_steps=() if review_run.llm_config.enabled else ("llm_enhance", "llm_document_audit", "llm_chapter_summary", "llm_legal_reasoning"),
            message=f"审查完成：{review_run.review.document_name}",
            result=payload,
            partial_result_available=False,
        )
    except Exception as exc:
        mark_review_job(
            job_id,
            status="failed",
            fail_steps=("parse", "base_scan", "llm_enhance", "finalize"),
            message=f"审查失败：{exc}",
            error=str(exc),
        )


def build_review_web_payload(review_run: ComplianceReviewRunResult) -> dict[str, Any]:
    payload = review_run.to_payload()
    payload["stage"] = build_stage_payload(review_run.normalized, review_run.review)
    payload["document"] = build_document_payload(review_run.normalized)
    return payload


def build_document_payload(normalized: NormalizedDocument) -> dict[str, Any]:
    text = Path(normalized.normalized_text_path).read_text(encoding="utf-8")
    lines = [
        {
            "number": number,
            "text": raw_line,
            "page_hint": page_hint_for_line(number, normalized.page_map),
        }
        for number, raw_line in enumerate(text.splitlines(), start=1)
    ]
    payload = {
        "source_path": normalized.source_path,
        "normalized_text_path": normalized.normalized_text_path,
        "line_count": len(lines),
        "lines": lines,
        "render_mode": "text",
        "blocks": [],
    }
    if Path(normalized.source_path).suffix.lower() == ".docx":
        blocks = _build_docx_blocks(Path(normalized.source_path), lines)
        if blocks:
            payload["render_mode"] = "docx_blocks"
            payload["blocks"] = blocks
    return payload


def build_stage_payload(normalized: NormalizedDocument, review: ReviewResult) -> dict[str, Any]:
    stage_profile = route_procurement_stage(document=normalized, findings=review.findings)
    classification = classify_procurement_catalog(normalized)
    return {
        "stage_key": stage_profile.stage_key,
        "stage_name": stage_profile.stage_name,
        "stage_goal": stage_profile.stage_goal,
        "review_posture": stage_profile.review_posture,
        "primary_users": list(stage_profile.primary_users),
        "output_bias": list(stage_profile.output_bias),
        "primary_catalog_name": classification.primary_catalog_name,
        "secondary_catalog_names": list(classification.secondary_catalog_names),
        "is_mixed_scope": classification.is_mixed_scope,
        "catalog_confidence": classification.catalog_confidence,
    }


def _build_docx_blocks(source_path: Path, lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        with ZipFile(source_path) as archive:
            document_xml = archive.read("word/document.xml")
    except Exception:
        return []

    root = ET.fromstring(document_xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    body = root.find("w:body", ns)
    if body is None:
        return []

    normalized_lines = [str(item["text"]) for item in lines]
    search_cursor = 0
    blocks: list[dict[str, Any]] = []
    block_index = 1

    for child in body:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _docx_paragraph_text(child)
            if not text.strip():
                continue
            start_line, end_line, search_cursor = _locate_block_lines(text, normalized_lines, search_cursor)
            blocks.append(
                {"block_id": f"block-{block_index}", "kind": "paragraph", "html": f"<p>{html_escape(text)}</p>", "start_line": start_line, "end_line": end_line, "page_hint": None}
            )
            block_index += 1
        elif tag == "tbl":
            rows = _docx_table_rows(child, ns)
            if not rows:
                continue
            table_text = "\n".join(" | ".join(cell for cell in row if cell) for row in rows if any(cell for cell in row))
            start_line, end_line, search_cursor = _locate_block_lines(table_text, normalized_lines, search_cursor)
            rows_html = []
            for row in rows:
                cells_html = "".join(f"<td>{html_escape(cell)}</td>" for cell in row)
                rows_html.append(f"<tr>{cells_html}</tr>")
            blocks.append(
                {"block_id": f"block-{block_index}", "kind": "table", "html": f"<table><tbody>{''.join(rows_html)}</tbody></table>", "start_line": start_line, "end_line": end_line, "page_hint": None}
            )
            block_index += 1
    return blocks


def _docx_paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag == "tab":
            parts.append("    ")
        elif tag in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def _docx_table_rows(table: ET.Element, ns: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("w:tr", ns):
        cells: list[str] = []
        for cell in row.findall("w:tc", ns):
            paragraphs = [_docx_paragraph_text(paragraph) for paragraph in cell.findall("w:p", ns)]
            cell_text = "\n".join(part for part in paragraphs if part).strip()
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def _locate_block_lines(block_text: str, normalized_lines: list[str], cursor: int) -> tuple[int, int, int]:
    target_parts = [part.strip() for part in block_text.splitlines() if part.strip()]
    if not target_parts:
        fallback = min(cursor + 1, max(len(normalized_lines), 1))
        return fallback, fallback, fallback
    start_index = None
    search_text = target_parts[0]
    for idx in range(cursor, len(normalized_lines)):
        candidate = normalized_lines[idx].strip()
        if candidate and (search_text in candidate or candidate in search_text):
            start_index = idx
            break
    if start_index is None:
        for idx, candidate_line in enumerate(normalized_lines):
            candidate = candidate_line.strip()
            if candidate and (search_text in candidate or candidate in search_text):
                start_index = idx
                break
    if start_index is None:
        fallback = min(cursor + 1, max(len(normalized_lines), 1))
        return fallback, fallback, fallback
    end_index = start_index
    part_cursor = start_index
    for part in target_parts[1:]:
        for idx in range(part_cursor + 1, len(normalized_lines)):
            candidate = normalized_lines[idx].strip()
            if candidate and (part in candidate or candidate in part):
                end_index = idx
                part_cursor = idx
                break
    return start_index + 1, end_index + 1, max(end_index + 1, cursor)
