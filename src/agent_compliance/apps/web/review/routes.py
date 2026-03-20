from __future__ import annotations

import json
import subprocess
import threading
import time
import uuid
from html import escape as html_escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from agent_compliance.agents.compliance_review.pipelines.llm_enhance import enhance_review_result
from agent_compliance.agents.compliance_review.pipelines.llm_review import apply_llm_review_tasks
from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import route_procurement_stage
from agent_compliance.agents.compliance_review.pipelines.render import write_review_outputs
from agent_compliance.agents.compliance_review.pipelines.review import build_review_result
from agent_compliance.agents.compliance_review.pipelines.review_export import export_review_bytes, write_export_output
from agent_compliance.agents.compliance_review.pipelines.rule_scan import run_rule_scan
from agent_compliance.agents.compliance_review.rules.base import RULE_SET_VERSION
from agent_compliance.apps.web.shared.http import parse_multipart, send_json
from agent_compliance.core.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.core.config import LLMConfig, detect_llm_config, detect_paths, detect_tender_parser_mode
from agent_compliance.core.knowledge.procurement_catalog import classify_procurement_catalog
from agent_compliance.core.parsers.pagination import page_hint_for_line
from agent_compliance.core.pipelines.normalize import run_normalize
from agent_compliance.core.schemas import NormalizedDocument, ReviewResult


REVIEW_JOB_LOCK = threading.Lock()
REVIEW_JOBS: dict[str, dict[str, Any]] = {}
BUYER_PROGRESS_STEPS = (
    {
        "key": "parse",
        "label": "文档解析中",
        "description": "正在提取正文、章节和表格内容。",
    },
    {
        "key": "base_scan",
        "label": "基础风险扫描中",
        "description": "正在识别资格、评分、技术、商务/验收风险。",
    },
    {
        "key": "llm_enhance",
        "label": "智能增强分析中",
        "description": "正在补充边界问题、章节主问题和法规解释。",
    },
    {
        "key": "finalize",
        "label": "结果收束中",
        "description": "正在去重、合并主问题、整理证据和建议。",
    },
    {
        "key": "done",
        "label": "审查完成",
        "description": "可查看问题清单和导出结果。",
    },
)
BUYER_TECHNICAL_STEPS = (
    {"key": "catalog", "label": "品目识别"},
    {"key": "rule_scan", "label": "规则扫描"},
    {"key": "scoring", "label": "评分语义分析"},
    {"key": "mixed_scope", "label": "混合边界分析"},
    {"key": "commercial", "label": "商务链路分析"},
    {"key": "llm_document_audit", "label": "全文辅助扫描"},
    {"key": "llm_chapter_summary", "label": "章节级总结"},
    {"key": "llm_legal_reasoning", "label": "法规适用逻辑解释"},
    {"key": "arbiter", "label": "仲裁归并"},
    {"key": "evidence", "label": "证据选择"},
)


def handle_open_source(handler: BaseHTTPRequestHandler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        path = Path(payload.get("path", ""))
        if not path.exists():
            send_json(handler, {"error": "原文件不存在"}, status=HTTPStatus.BAD_REQUEST)
            return
        subprocess.run(["open", str(path)], check=True)
        send_json(handler, {"ok": True})
    except Exception as exc:
        send_json(handler, {"error": f"打开原文件失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def handle_export_review(handler: BaseHTTPRequestHandler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        review_payload = payload.get("review")
        if not isinstance(review_payload, dict):
            send_json(handler, {"error": "缺少 review 结果"}, status=HTTPStatus.BAD_REQUEST)
            return
        export_format = str(payload.get("format", "json")).strip().lower()
        mode = str(payload.get("mode", "summary")).strip().lower()
        review = ReviewResult.from_dict(review_payload)
        document_payload = payload.get("document") if isinstance(payload.get("document"), dict) else None
        stage_payload = payload.get("stage") if isinstance(payload.get("stage"), dict) else None
        if document_payload is not None and stage_payload:
            document_payload = {**document_payload, **stage_payload}
        content, content_type, filename = export_review_bytes(
            review,
            export_format=export_format,
            mode=mode,
            document_payload=document_payload,
        )
        write_export_output(
            review,
            export_format=export_format,
            mode=mode,
            document_payload=document_payload,
        )
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Disposition", _build_download_content_disposition(filename))
        handler.send_header("Content-Length", str(len(content)))
        handler.end_headers()
        handler.wfile.write(content)
    except Exception as exc:
        send_json(handler, {"error": f"导出失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def handle_review_start(handler: BaseHTTPRequestHandler) -> None:
    try:
        body = handler.rfile.read(int(handler.headers.get("Content-Length", "0")))
        fields = parse_multipart(handler.headers, body)
    except Exception as exc:
        send_json(handler, {"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
        return

    upload = fields.get("file")
    if not upload or not upload.get("filename"):
        send_json(handler, {"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
        return

    use_llm = _flag_value(fields.get("use_llm", {}).get("value"))
    use_cache = _flag_value(fields.get("use_cache", {}).get("value"))
    parser_mode = str(fields.get("tender_parser_mode", {}).get("value") or detect_tender_parser_mode()).strip().lower()
    source_path = _persist_upload(str(upload["filename"]), bytes(upload["content"]))
    job_id = _create_review_job(
        Path(source_path).name,
        source_path,
        use_cache=use_cache,
        use_llm=use_llm,
        parser_mode=parser_mode,
    )
    worker = threading.Thread(
        target=_run_review_job,
        args=(job_id, source_path, use_cache, use_llm, parser_mode, detect_paths()),
        daemon=True,
    )
    worker.start()
    send_json(
        handler,
        {
            "job_id": job_id,
            "status": "queued",
            "parser": {"mode": parser_mode, "enabled": parser_mode != "off"},
        },
    )


def handle_review_status(handler: BaseHTTPRequestHandler, query: str) -> None:
    job_id = parse_qs(query).get("job_id", [""])[0].strip()
    if not job_id:
        send_json(handler, {"error": "缺少 job_id"}, status=HTTPStatus.BAD_REQUEST)
        return
    payload = _review_job_status_payload(job_id)
    if payload is None:
        send_json(handler, {"error": "任务不存在"}, status=HTTPStatus.NOT_FOUND)
        return
    send_json(handler, payload)


def handle_review_result(handler: BaseHTTPRequestHandler, query: str) -> None:
    job_id = parse_qs(query).get("job_id", [""])[0].strip()
    if not job_id:
        send_json(handler, {"error": "缺少 job_id"}, status=HTTPStatus.BAD_REQUEST)
        return
    payload = _review_job_result_payload(job_id)
    if payload is None:
        send_json(handler, {"error": "任务不存在"}, status=HTTPStatus.NOT_FOUND)
        return
    if payload.get("status") == "failed":
        send_json(handler, payload, status=HTTPStatus.BAD_REQUEST)
        return
    if payload.get("status") != "completed":
        send_json(handler, payload, status=HTTPStatus.ACCEPTED)
        return
    send_json(handler, payload["result"])


def handle_review_submit(handler: BaseHTTPRequestHandler) -> None:
    try:
        body = handler.rfile.read(int(handler.headers.get("Content-Length", "0")))
        fields = parse_multipart(handler.headers, body)
    except Exception as exc:
        send_json(handler, {"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
        return

    upload = fields.get("file")
    if not upload or not upload.get("filename"):
        send_json(handler, {"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
        return

    use_llm = _flag_value(fields.get("use_llm", {}).get("value"))
    use_cache = _flag_value(fields.get("use_cache", {}).get("value"))
    paths = detect_paths()
    source_path = _persist_upload(str(upload["filename"]), bytes(upload["content"]))
    normalized = run_normalize(source_path)
    parser_mode = str(fields.get("tender_parser_mode", {}).get("value") or detect_tender_parser_mode()).strip().lower()
    review, llm_artifacts, cache_key, cache_used = _run_review(
        normalized,
        use_cache=use_cache,
        use_llm=use_llm,
        parser_mode=parser_mode,
        paths=paths,
    )
    json_path, md_path = write_review_outputs(review, normalized.file_hash[:12])

    send_json(
        handler,
        {
            "cache": {"enabled": use_cache, "used": cache_used, "key": cache_key},
            "llm": {
                "enabled": _web_llm_config(use_llm).enabled,
                "base_url": detect_llm_config().base_url,
                "model": detect_llm_config().model,
            },
            "parser": {"mode": parser_mode, "enabled": parser_mode != "off"},
            "stage": _build_stage_payload(normalized, review),
            "document": _build_document_payload(normalized),
            "review": review.to_dict(),
            "llm_review": llm_artifacts.to_dict(),
            "outputs": {"json": str(json_path), "markdown": str(md_path)},
        },
    )


def _now_ts() -> float:
    return time.time()


def _initial_progress_steps() -> list[dict[str, Any]]:
    return [dict(item, status="pending") for item in BUYER_PROGRESS_STEPS]


def _initial_technical_steps() -> list[dict[str, Any]]:
    return [dict(item, status="pending") for item in BUYER_TECHNICAL_STEPS]


def _create_review_job(filename: str, source_path: Path, *, use_cache: bool, use_llm: bool, parser_mode: str) -> str:
    job_id = f"review-{uuid.uuid4().hex[:12]}"
    stage_profile = route_procurement_stage()
    now = _now_ts()
    with REVIEW_JOB_LOCK:
        REVIEW_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "mode": "hybrid" if use_llm else "code",
            "stage_profile": {
                "stage_key": stage_profile.stage_key,
                "stage_name": stage_profile.stage_name,
                "stage_goal": stage_profile.stage_goal,
                "review_posture": stage_profile.review_posture,
                "output_bias": list(stage_profile.output_bias),
            },
            "document_name": filename,
            "source_path": str(source_path),
            "progress": {
                "current_step": "parse",
                "steps": _initial_progress_steps(),
                "technical_steps": _initial_technical_steps(),
            },
            "partial_result_available": False,
            "last_message": "任务已创建，等待开始。",
            "started_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
            "use_cache": use_cache,
            "use_llm": use_llm,
            "parser_mode": parser_mode,
        }
    return job_id


def _set_step_status(job: dict[str, Any], step_key: str, status: str) -> None:
    for step in job["progress"]["steps"]:
        if step["key"] == step_key:
            step["status"] = status
            break
    for step in job["progress"]["technical_steps"]:
        if step["key"] == step_key:
            step["status"] = status
            break


def _mark_review_job(
    job_id: str,
    *,
    status: str | None = None,
    current_step: str | None = None,
    message: str | None = None,
    complete_steps: tuple[str, ...] = (),
    run_steps: tuple[str, ...] = (),
    skip_steps: tuple[str, ...] = (),
    fail_steps: tuple[str, ...] = (),
    result: dict[str, Any] | None = None,
    error: str | None = None,
    partial_result_available: bool | None = None,
) -> None:
    with REVIEW_JOB_LOCK:
        job = REVIEW_JOBS.get(job_id)
        if job is None:
            return
        if status:
            job["status"] = status
        if current_step:
            job["progress"]["current_step"] = current_step
        for step_key in complete_steps:
            _set_step_status(job, step_key, "completed")
        for step_key in run_steps:
            _set_step_status(job, step_key, "running")
        for step_key in skip_steps:
            _set_step_status(job, step_key, "skipped")
        for step_key in fail_steps:
            _set_step_status(job, step_key, "failed")
        if message is not None:
            job["last_message"] = message
        if partial_result_available is not None:
            job["partial_result_available"] = partial_result_available
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        job["updated_at"] = _now_ts()


def _review_job_status_payload(job_id: str) -> dict[str, Any] | None:
    with REVIEW_JOB_LOCK:
        job = REVIEW_JOBS.get(job_id)
        if job is None:
            return None
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "mode": job["mode"],
            "parser": {"mode": job.get("parser_mode", "off"), "enabled": job.get("parser_mode", "off") != "off"},
            "stage_profile": job["stage_profile"],
            "document_name": job["document_name"],
            "progress": job["progress"],
            "partial_result_available": job["partial_result_available"],
            "last_message": job["last_message"],
            "started_at": job["started_at"],
            "updated_at": job["updated_at"],
            "error": job["error"],
        }


def _review_job_result_payload(job_id: str) -> dict[str, Any] | None:
    with REVIEW_JOB_LOCK:
        job = REVIEW_JOBS.get(job_id)
        if job is None:
            return None
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "error": job["error"],
            "result": job["result"],
        }


def _run_review_job(job_id: str, source_path: Path, use_cache: bool, use_llm: bool, parser_mode: str, paths: Any) -> None:
    _mark_review_job(
        job_id,
        status="running",
        current_step="parse",
        run_steps=("parse",),
        message="正在解析文档、提取正文、章节和表格内容。",
    )
    try:
        normalized = run_normalize(source_path)
        _mark_review_job(
            job_id,
            current_step="base_scan",
            complete_steps=("parse", "catalog"),
            run_steps=("base_scan", "rule_scan"),
            message="正在扫描基础条款，识别资格、评分、技术、商务/验收风险。",
        )

        reference_snapshot = reference_snapshot_id(paths.repo_root / "docs" / "references")
        cache_key = build_review_cache_key(
            file_hash=normalized.file_hash,
            rule_set_version=RULE_SET_VERSION,
            reference_snapshot=reference_snapshot,
            parser_mode=parser_mode,
            review_pipeline_version=REVIEW_CACHE_VERSION,
        )
        review = load_review_cache(cache_key) if use_cache else None
        cache_used = review is not None
        if review is None:
            hits = run_rule_scan(normalized)
            _mark_review_job(
                job_id,
                complete_steps=("rule_scan",),
                run_steps=("scoring", "mixed_scope", "commercial"),
                message="正在扫描评分条款，并分析混合边界和商务链条。",
            )
            review = build_review_result(normalized, hits, parser_mode=parser_mode)
            if use_cache:
                save_review_cache(
                    cache_key,
                    review,
                    metadata={
                        "file_hash": normalized.file_hash,
                        "rule_set_version": RULE_SET_VERSION,
                        "reference_snapshot": reference_snapshot,
                        "parser_mode": parser_mode,
                        "review_pipeline_version": REVIEW_CACHE_VERSION,
                    },
                )
            base_message = "基础风险扫描完成，正在准备智能增强分析。"
        else:
            base_message = "已复用缓存结果，正在准备智能增强分析。"
        _mark_review_job(
            job_id,
            complete_steps=("base_scan", "rule_scan", "scoring", "mixed_scope", "commercial"),
            message=base_message,
        )

        llm_config = _web_llm_config(use_llm)
        llm_completed_steps: tuple[str, ...] = ()
        if llm_config.enabled:
            _mark_review_job(
                job_id,
                current_step="llm_enhance",
                run_steps=("llm_enhance", "llm_document_audit"),
                message="正在进行全文辅助扫描，补充规则未稳定命中的边界问题。",
            )
            llm_completed_steps = ("llm_enhance", "llm_document_audit", "llm_chapter_summary", "llm_legal_reasoning")
        else:
            _mark_review_job(
                job_id,
                current_step="finalize",
                skip_steps=("llm_enhance", "llm_document_audit", "llm_chapter_summary", "llm_legal_reasoning"),
                message="未启用大模型（混合审查），直接进入结果收束。",
            )

        review = enhance_review_result(review, llm_config)
        if llm_config.enabled:
            _mark_review_job(
                job_id,
                current_step="llm_enhance",
                complete_steps=("llm_document_audit",),
                run_steps=("llm_chapter_summary",),
                message="正在汇总章节主问题，收束评分、技术和商务章节的关键风险。",
            )
        review, llm_artifacts = apply_llm_review_tasks(
            normalized,
            review,
            llm_config,
            output_stem=normalized.file_hash[:12],
        )
        if llm_config.enabled:
            _mark_review_job(
                job_id,
                current_step="llm_enhance",
                complete_steps=("llm_chapter_summary",),
                run_steps=("llm_legal_reasoning",),
                message="正在生成法规适用逻辑，说明哪些问题应直接修改、论证或复核。",
            )
        _mark_review_job(
            job_id,
            current_step="finalize",
            complete_steps=llm_completed_steps,
            run_steps=("finalize", "arbiter", "evidence"),
            message="正在收束结果，去重、合并主问题并整理证据。",
        )

        json_path, md_path = write_review_outputs(review, normalized.file_hash[:12])
        payload = {
            "cache": {"enabled": use_cache, "used": cache_used, "key": cache_key},
            "llm": {
                "enabled": llm_config.enabled,
                "base_url": detect_llm_config().base_url,
                "model": detect_llm_config().model,
            },
            "parser": {"mode": parser_mode, "enabled": parser_mode != "off"},
            "stage": _build_stage_payload(normalized, review),
            "document": _build_document_payload(normalized),
            "review": review.to_dict(),
            "llm_review": llm_artifacts.to_dict(),
            "outputs": {"json": str(json_path), "markdown": str(md_path)},
        }
        _mark_review_job(
            job_id,
            status="completed",
            current_step="done",
            complete_steps=("finalize", "arbiter", "evidence", "done"),
            message=f"审查完成：{review.document_name}",
            result=payload,
            partial_result_available=False,
        )
    except Exception as exc:
        _mark_review_job(
            job_id,
            status="failed",
            fail_steps=("parse", "base_scan", "llm_enhance", "finalize"),
            message=f"审查失败：{exc}",
            error=str(exc),
        )


def _run_review(
    normalized: NormalizedDocument,
    *,
    use_cache: bool,
    use_llm: bool,
    parser_mode: str,
    paths: Any,
) -> tuple[ReviewResult, Any, str, bool]:
    reference_snapshot = reference_snapshot_id(paths.repo_root / "docs" / "references")
    cache_key = build_review_cache_key(
        file_hash=normalized.file_hash,
        rule_set_version=RULE_SET_VERSION,
        reference_snapshot=reference_snapshot,
        parser_mode=parser_mode,
        review_pipeline_version=REVIEW_CACHE_VERSION,
    )
    review = load_review_cache(cache_key) if use_cache else None
    cache_used = review is not None
    if review is None:
        hits = run_rule_scan(normalized)
        review = build_review_result(normalized, hits, parser_mode=parser_mode)
        if use_cache:
            save_review_cache(
                cache_key,
                review,
                metadata={
                    "file_hash": normalized.file_hash,
                    "rule_set_version": RULE_SET_VERSION,
                    "reference_snapshot": reference_snapshot,
                    "parser_mode": parser_mode,
                    "review_pipeline_version": REVIEW_CACHE_VERSION,
                },
            )
    review = enhance_review_result(review, _web_llm_config(use_llm))
    review, llm_artifacts = apply_llm_review_tasks(
        normalized,
        review,
        _web_llm_config(use_llm),
        output_stem=normalized.file_hash[:12],
    )
    return review, llm_artifacts, cache_key, cache_used


def _persist_upload(filename: str, content: bytes) -> Path:
    paths = detect_paths()
    paths.uploads_root.mkdir(parents=True, exist_ok=True)
    target = paths.uploads_root / Path(filename).name
    target.write_bytes(content)
    return target


def _build_download_content_disposition(filename: str) -> str:
    ascii_name = "".join(ch if ord(ch) < 128 else "_" for ch in filename)
    if not ascii_name.strip("._"):
        ascii_name = "review-export"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"


def _web_llm_config(use_llm: bool) -> LLMConfig:
    config = detect_llm_config()
    return LLMConfig(
        enabled=bool(use_llm or config.enabled),
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )


def _flag_value(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "on", "yes"}


def _build_document_payload(normalized: NormalizedDocument) -> dict[str, Any]:
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
    suffix = Path(normalized.source_path).suffix.lower()
    if suffix == ".docx":
        blocks = _build_docx_blocks(Path(normalized.source_path), lines)
        if blocks:
            payload["render_mode"] = "docx_blocks"
            payload["blocks"] = blocks
    return payload


def _build_stage_payload(normalized: NormalizedDocument, review: ReviewResult) -> dict[str, Any]:
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
                {
                    "block_id": f"block-{block_index}",
                    "kind": "paragraph",
                    "html": f"<p>{html_escape(text)}</p>",
                    "start_line": start_line,
                    "end_line": end_line,
                    "page_hint": None,
                }
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
                {
                    "block_id": f"block-{block_index}",
                    "kind": "table",
                    "html": f"<table><tbody>{''.join(rows_html)}</tbody></table>",
                    "start_line": start_line,
                    "end_line": end_line,
                    "page_hint": None,
                }
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
        if not candidate:
            continue
        if search_text in candidate or candidate in search_text:
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


__all__ = [
    "handle_export_review",
    "handle_open_source",
    "handle_review_result",
    "handle_review_start",
    "handle_review_status",
    "handle_review_submit",
]
