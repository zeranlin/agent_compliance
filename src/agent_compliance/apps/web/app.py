from __future__ import annotations

import json
import subprocess
import threading
import time
import uuid
from html import escape as html_escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from agent_compliance.core.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.core.config import LLMConfig, detect_llm_config, detect_paths, detect_tender_parser_mode
from agent_compliance.apps.web.incubator.page import incubator_html
from agent_compliance.apps.web.review import review_buyer_html, review_next_html
from agent_compliance.apps.web.incubator.routes import (
    handle_incubator_run_detail,
    handle_incubator_start,
    incubator_blueprints_payload,
    list_incubator_runs,
)
from agent_compliance.apps.web.rules.page import rules_html
from agent_compliance.apps.web.rules.routes import handle_rule_decision, rules_payload
from agent_compliance.apps.web.shared.http import parse_multipart, send_html, send_json
from agent_compliance.core.knowledge.procurement_catalog import classify_procurement_catalog
from agent_compliance.core.parsers.pagination import page_hint_for_line
from agent_compliance.agents.compliance_review.pipelines.llm_enhance import enhance_review_result
from agent_compliance.agents.compliance_review.pipelines.llm_review import apply_llm_review_tasks
from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import route_procurement_stage
from agent_compliance.agents.compliance_review.pipelines.review_export import export_review_bytes, write_export_output
from agent_compliance.core.pipelines.normalize import run_normalize
from agent_compliance.agents.compliance_review.pipelines.render import write_review_outputs
from agent_compliance.agents.compliance_review.pipelines.review import build_review_result
from agent_compliance.agents.compliance_review.pipelines.rule_scan import run_rule_scan
from agent_compliance.agents.compliance_review.rules.base import RULE_SET_VERSION
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


def run_web_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), ReviewWebHandler)
    print(f"Web UI running at http://{host}:{port}")
    server.serve_forever()


class ReviewWebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_html(_index_html())
            return
        if path == "/review-buyer":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/review-check")
            self.end_headers()
            return
        if path == "/review-next":
            self._send_html(review_next_html())
            return
        if path == "/review-check":
            self._send_html(review_buyer_html())
            return
        if path == "/review-fresh":
            self._send_html(_review_fresh_html())
            return
        if path == "/rules":
            self._send_html(rules_html())
            return
        if path == "/incubator":
            self._send_html(incubator_html())
            return
        if path == "/api/rules":
            self._send_json(rules_payload())
            return
        if path == "/api/incubator/blueprints":
            self._send_json({"blueprints": incubator_blueprints_payload()})
            return
        if path == "/api/incubator/runs":
            self._send_json({"runs": list_incubator_runs()})
            return
        if path == "/api/incubator/run":
            handle_incubator_run_detail(self, parsed.query)
            return
        if path == "/api/review-status":
            self._handle_review_status(parsed.query)
            return
        if path == "/api/review-result":
            self._handle_review_result(parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/open-source":
            self._handle_open_source()
            return
        if path == "/api/export-review":
            self._handle_export_review()
            return
        if path == "/api/rules/decision":
            handle_rule_decision(self)
            return
        if path == "/api/incubator/start":
            handle_incubator_start(self)
            return
        if path == "/api/review-start":
            self._handle_review_start()
            return
        if path != "/api/review":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            fields = parse_multipart(self.headers, body)
        except Exception as exc:
            self._send_json({"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        upload = fields.get("file")
        if not upload or not upload.get("filename"):
            self._send_json({"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
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

        self._send_json(
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
            }
        )

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, html: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        send_html(self, html, status=status)

    def _send_json(self, payload: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        send_json(self, payload, status=status)

    def _handle_open_source(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            path = Path(payload.get("path", ""))
            if not path.exists():
                self._send_json({"error": "原文件不存在"}, status=HTTPStatus.BAD_REQUEST)
                return
            subprocess.run(["open", str(path)], check=True)
            self._send_json({"ok": True})
        except Exception as exc:
            self._send_json({"error": f"打开原文件失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)

    def _handle_export_review(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            review_payload = payload.get("review")
            if not isinstance(review_payload, dict):
                self._send_json({"error": "缺少 review 结果"}, status=HTTPStatus.BAD_REQUEST)
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
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", _build_download_content_disposition(filename))
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as exc:
            self._send_json({"error": f"导出失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)

    def _handle_review_start(self) -> None:
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            fields = parse_multipart(self.headers, body)
        except Exception as exc:
            self._send_json({"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        upload = fields.get("file")
        if not upload or not upload.get("filename"):
            self._send_json({"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
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
        self._send_json({"job_id": job_id, "status": "queued", "parser": {"mode": parser_mode, "enabled": parser_mode != "off"}})

    def _handle_review_status(self, query: str) -> None:
        job_id = parse_qs(query).get("job_id", [""])[0].strip()
        if not job_id:
            self._send_json({"error": "缺少 job_id"}, status=HTTPStatus.BAD_REQUEST)
            return
        payload = _review_job_status_payload(job_id)
        if payload is None:
            self._send_json({"error": "任务不存在"}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_json(payload)

    def _handle_review_result(self, query: str) -> None:
        job_id = parse_qs(query).get("job_id", [""])[0].strip()
        if not job_id:
            self._send_json({"error": "缺少 job_id"}, status=HTTPStatus.BAD_REQUEST)
            return
        payload = _review_job_result_payload(job_id)
        if payload is None:
            self._send_json({"error": "任务不存在"}, status=HTTPStatus.NOT_FOUND)
            return
        if payload.get("status") == "failed":
            self._send_json(payload, status=HTTPStatus.BAD_REQUEST)
            return
        if payload.get("status") != "completed":
            self._send_json(payload, status=HTTPStatus.ACCEPTED)
            return
        self._send_json(payload["result"])


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


def _run_review_job(job_id: str, source_path: Path, use_cache: bool, use_llm: bool, parser_mode: str, paths) -> None:
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
    paths,
) -> tuple[Any, str, bool]:
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
            text = _docx_paragraph_text(child, ns)
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
                    "page_hint": page_hint_for_line(start_line, []) if False else None,
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


def _docx_paragraph_text(paragraph: ET.Element, ns: dict[str, str]) -> str:
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
            paragraphs = [_docx_paragraph_text(paragraph, ns) for paragraph in cell.findall("w:p", ns)]
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


def _index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>采购审查工作台</title>
  <style>
    :root {
      --bg: #f4efe5;
      --panel: #fffdf8;
      --line: #ddd2c2;
      --ink: #20252b;
      --muted: #6c675e;
      --accent: #9d4a24;
      --high: #a33d22;
      --medium: #8f6714;
      --active: #fff2dd;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
    }
    .app {
      max-width: 1500px;
      margin: 0 auto;
      padding: 20px;
    }
    .hero {
      margin-bottom: 16px;
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: 30px;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 12px 30px rgba(52, 41, 29, 0.06);
    }
    .toolbar {
      padding: 16px;
      margin-bottom: 16px;
      display: grid;
      gap: 12px;
    }
    .toolbar-row {
      display: flex;
      flex-wrap: wrap;
      gap: 12px 16px;
      align-items: center;
    }
    button {
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: #fff;
      padding: 10px 16px;
      font-size: 14px;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--ink);
      border: 1px solid var(--line);
    }
    button:disabled {
      opacity: .5;
      cursor: wait;
    }
    label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 14px;
    }
    .status {
      color: var(--muted);
      font-size: 14px;
    }
    .summary {
      display: none;
      margin-bottom: 16px;
      padding: 16px;
    }
    .summary h2 {
      margin: 0 0 10px;
      font-size: 20px;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: #fff;
    }
    .stat .label {
      color: var(--muted);
      font-size: 12px;
    }
    .stat .value {
      margin-top: 8px;
      font-size: 18px;
      font-weight: 700;
      line-height: 1.5;
      word-break: break-word;
    }
    .workspace {
      display: none;
      grid-template-columns: 420px minmax(0, 1fr);
      gap: 16px;
      align-items: start;
    }
    .rules-panel {
      display: none;
      margin-top: 16px;
      padding: 16px;
    }
    .rules-grid {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 16px;
      margin-top: 12px;
    }
    .rules-col {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      min-height: 420px;
      overflow: hidden;
    }
    .rules-col-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 6px;
    }
    .rules-col-head h3 {
      margin: 0;
      font-size: 18px;
    }
    .rules-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-top: 8px;
    }
    .rules-list {
      padding: 12px;
      display: grid;
      gap: 10px;
      max-height: 560px;
      overflow: auto;
    }
    .rule-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
      background: #fffdfa;
      display: grid;
      gap: 8px;
      cursor: pointer;
    }
    .rule-card.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(157, 74, 36, 0.12);
      background: #fff8f1;
    }
    .rule-card-title {
      font-size: 15px;
      font-weight: 700;
      line-height: 1.5;
    }
    .rule-card-meta {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
      word-break: break-word;
    }
    .rule-detail {
      padding: 16px;
      display: grid;
      gap: 12px;
    }
    .rule-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .rule-note {
      width: 100%;
      min-height: 70px;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      font: inherit;
      resize: vertical;
    }
    .issues,
    .document {
      min-height: 580px;
    }
    .issues-head,
    .document-head {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 8px;
    }
    .issues-head h2,
    .document-head h2 {
      margin: 0;
      font-size: 20px;
    }
    .meta {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      word-break: break-word;
    }
    .issues-list {
      padding: 12px;
      display: grid;
      gap: 10px;
      max-height: calc(100vh - 250px);
      overflow: auto;
    }
    .issues-summary-bar {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-top: 6px;
    }
    .issues-stat {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 10px 12px;
      display: grid;
      gap: 4px;
    }
    .issues-stat-label {
      color: var(--muted);
      font-size: 12px;
    }
    .issues-stat-value {
      font-size: 20px;
      font-weight: 700;
      line-height: 1.1;
    }
    .issues-stat-value.high {
      color: var(--high);
    }
    .issues-stat-value.medium {
      color: var(--medium);
    }
    .issue-item {
      width: 100%;
      background: #fff;
      color: var(--ink);
      border: 1px solid var(--line);
      border-radius: 12px;
      display: grid;
      overflow: hidden;
    }
    .issue-item.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(157, 74, 36, 0.12);
      background: #fff8f1;
    }
    .issue-item.high {
      border-left: 5px solid var(--high);
      background: linear-gradient(90deg, rgba(163, 61, 34, 0.05), #fff 14%);
    }
    .issue-item.medium {
      border-left: 5px solid var(--medium);
      background: linear-gradient(90deg, rgba(143, 103, 20, 0.05), #fff 14%);
    }
    .issue-summary {
      width: 100%;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      padding: 14px;
      display: grid;
      gap: 8px;
      cursor: pointer;
    }
    .issue-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      justify-content: space-between;
    }
    .issue-action-buttons {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .issue-mini-btn {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--ink);
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
    }
    .issue-detail {
      display: none;
      padding: 0 14px 14px;
      border-top: 1px solid #f1eadf;
      background: rgba(255, 252, 247, 0.92);
    }
    .issue-item.expanded .issue-detail {
      display: grid;
      gap: 10px;
    }
    .detail-pair {
      display: grid;
      gap: 4px;
    }
    .detail-label {
      color: var(--muted);
      font-size: 12px;
    }
    .detail-value {
      color: var(--ink);
      font-size: 13px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .issue-top {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      background: #f5ede2;
      color: var(--accent);
    }
    .badge.high {
      background: rgba(163, 61, 34, 0.1);
      color: var(--high);
    }
    .badge.medium {
      background: rgba(143, 103, 20, 0.12);
      color: var(--medium);
    }
    .badge.origin-llm {
      background: rgba(40, 88, 162, 0.12);
      color: #2858a2;
    }
    .badge.origin-rule {
      background: rgba(61, 120, 74, 0.12);
      color: #2f6f42;
    }
    .issues-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .filter-chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
    }
    .filter-chip.active {
      border-color: var(--accent);
      color: var(--accent);
      background: #fff5ea;
    }
    .issue-title {
      font-size: 16px;
      font-weight: 700;
      line-height: 1.5;
    }
    .issue-title-row {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      justify-content: space-between;
    }
    .issue-rank {
      min-width: 34px;
      height: 34px;
      border-radius: 10px;
      background: #f5ede2;
      color: var(--accent);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      flex: 0 0 auto;
    }
    .issue-rank.high {
      background: rgba(163, 61, 34, 0.12);
      color: var(--high);
    }
    .issue-rank.medium {
      background: rgba(143, 103, 20, 0.12);
      color: var(--medium);
    }
    .issue-main {
      display: grid;
      gap: 6px;
      min-width: 0;
      flex: 1 1 auto;
    }
    .issue-meta,
    .issue-snippet {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .issue-snippet {
      color: var(--ink);
      background: #fffaf3;
      border-radius: 10px;
      padding: 9px 10px;
    }
    .issue-toggle-text {
      color: var(--muted);
      font-size: 12px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 12px;
    }
    .document-body {
      max-height: calc(100vh - 250px);
      overflow: auto;
      padding: 8px 0;
      background: #fff;
    }
    .doc-block {
      margin: 12px 16px;
      padding: 10px 12px;
      border: 1px solid transparent;
      border-radius: 10px;
      background: #fff;
    }
    .doc-block.active {
      background: var(--active);
      border-color: #f0c98a;
    }
    .doc-block p {
      margin: 0;
      line-height: 1.8;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .doc-block table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      background: #fff;
    }
    .doc-block td {
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.7;
      font-size: 14px;
    }
    .doc-block-meta {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .doc-line {
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr);
      gap: 12px;
      padding: 8px 16px;
      border-top: 1px solid #f1eadf;
      align-items: start;
    }
    .doc-line:first-child {
      border-top: 0;
    }
    .doc-line.active {
      background: var(--active);
      border-top-color: #f0c98a;
      border-bottom: 1px solid #f0c98a;
    }
    .doc-line-number {
      text-align: right;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .doc-line-text {
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.7;
      font-size: 14px;
    }
    .empty {
      padding: 20px 16px;
      color: var(--muted);
      line-height: 1.7;
    }
    @media (max-width: 1080px) {
      .workspace {
        grid-template-columns: 1fr;
      }
      .rules-grid {
        grid-template-columns: 1fr;
      }
      .issues-list,
      .document-body {
        max-height: none;
      }
      .summary-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .issues-summary-bar,
      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <h1>采购审查工作台</h1>
      <p>上传采购文件后，页面会渲染文件正文并生成审查问题清单。点击任意问题，右侧正文会自动定位到对应位置并高亮，方便快速复核。</p>
      <p><a href="/review-check">打开采购人审查页</a> · <a href="/review-next">打开增强审查页</a> · <a href="/rules">打开规则管理页面</a> · <a href="/incubator">打开孵化工厂控制台</a></p>
    </section>

    <form id="review-form" class="panel toolbar">
      <div class="toolbar-row">
        <input type="file" name="file" accept=".docx,.doc,.pdf,.txt,.md,.rtf" required />
        <button type="submit" id="submit-btn">上传并审查</button>
        <button type="button" id="open-source-btn" class="secondary" disabled>打开原文件</button>
      </div>
      <div class="toolbar-row">
        <label><input type="checkbox" name="use_cache" /> 启用缓存</label>
        <label><input type="checkbox" name="use_llm" /> 启用大模型（混合审查）</label>
      </div>
      <div id="status" class="status">等待上传文件</div>
    </form>

    <section id="summary" class="panel summary"></section>

    <section id="workspace" class="workspace">
      <section class="panel issues">
        <div id="issues-head" class="issues-head"></div>
        <div id="issues-list" class="issues-list"></div>
      </section>
      <section class="panel document">
        <div id="document-head" class="document-head"></div>
        <div id="document-body" class="document-body"></div>
      </section>
    </section>
  </div>

  <script>
    const form = document.getElementById('review-form');
    const submitBtn = document.getElementById('submit-btn');
    const openSourceBtn = document.getElementById('open-source-btn');
    const statusNode = document.getElementById('status');
    const summaryNode = document.getElementById('summary');
    const workspaceNode = document.getElementById('workspace');
    const issuesHeadNode = document.getElementById('issues-head');
    const issuesListNode = document.getElementById('issues-list');
    const documentHeadNode = document.getElementById('document-head');
    const documentBodyNode = document.getElementById('document-body');
    let latestDocument = null;
    let latestFindings = [];
    let currentFindingFilter = 'all';

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      submitBtn.disabled = true;
      openSourceBtn.disabled = true;
      statusNode.textContent = '正在审查，请稍候...';
      summaryNode.style.display = 'none';
      workspaceNode.style.display = 'none';
      try {
        const formData = new FormData(form);
        const response = await fetch('/api/review', { method: 'POST', body: formData });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '审查失败');
        latestDocument = payload.document;
        latestFindings = payload.review.findings;
        currentFindingFilter = 'all';
        renderSummary(payload);
        renderIssues(payload.review.findings);
        renderDocument(payload.document);
        if (payload.review.findings.length) {
          selectFinding(payload.review.findings[0].finding_id);
        }
        openSourceBtn.disabled = !payload.document || !payload.document.source_path;
        statusNode.textContent = '审查完成';
      } catch (error) {
        statusNode.textContent = `失败：${error.message}`;
      } finally {
        submitBtn.disabled = false;
      }
    });

    openSourceBtn.addEventListener('click', openSourceFile);

    function renderSummary(payload) {
      const review = payload.review;
      const highCount = review.findings.filter((item) => item.risk_level === 'high').length;
      const mediumCount = review.findings.filter((item) => item.risk_level === 'medium').length;
      const llmAddedCount = review.findings.filter((item) => item.finding_origin === 'llm_added').length;
      const ruleCount = review.findings.filter((item) => item.finding_origin !== 'llm_added').length;
      summaryNode.innerHTML = `
        <h2>审查摘要</h2>
        <div>${escapeHtml(review.overall_risk_summary)}</div>
        <div class="summary-grid">
          <div class="stat"><div class="label">文件</div><div class="value">${escapeHtml(review.document_name)}</div></div>
          <div class="stat"><div class="label">发现项</div><div class="value">${review.findings.length}</div></div>
          <div class="stat"><div class="label">规则命中</div><div class="value">${ruleCount}</div></div>
          <div class="stat"><div class="label">模型新增</div><div class="value">${llmAddedCount}</div></div>
          <div class="stat"><div class="label">高风险</div><div class="value">${highCount}</div></div>
          <div class="stat"><div class="label">中风险</div><div class="value">${mediumCount}</div></div>
          <div class="stat"><div class="label">缓存 / 模型</div><div class="value">${payload.cache.enabled ? '缓存开' : '缓存关'} / ${payload.llm.enabled ? '模型开' : '模型关'}</div></div>
        </div>`;
      summaryNode.style.display = 'block';
    }


    function renderIssues(findings) {
      const sortedFindings = sortFindings(findings);
      const filtered = applyFindingFilter(sortedFindings, currentFindingFilter);
      const llmCount = findings.filter((item) => item.finding_origin === 'llm_added').length;
      const ruleCount = findings.filter((item) => item.finding_origin !== 'llm_added').length;
      const highCount = findings.filter((item) => item.risk_level === 'high').length;
      const mediumCount = findings.filter((item) => item.risk_level === 'medium').length;
      issuesHeadNode.innerHTML = `
        <h2>审查问题清单</h2>
        <div class="meta">共 ${findings.length} 条问题，其中规则命中 ${ruleCount} 条、模型新增 ${llmCount} 条。清单已按风险等级排序，高风险优先显示。点击“定位正文”会跳到对应位置，点击“展开详情”可查看依据、判断和建议。</div>
        <div class="issues-summary-bar">
          <div class="issues-stat"><div class="issues-stat-label">高风险</div><div class="issues-stat-value high">${highCount}</div></div>
          <div class="issues-stat"><div class="issues-stat-label">中风险</div><div class="issues-stat-value medium">${mediumCount}</div></div>
          <div class="issues-stat"><div class="issues-stat-label">规则命中</div><div class="issues-stat-value">${ruleCount}</div></div>
          <div class="issues-stat"><div class="issues-stat-label">模型新增</div><div class="issues-stat-value">${llmCount}</div></div>
        </div>
        <div class="issues-filters">
          <button type="button" class="filter-chip ${currentFindingFilter === 'all' ? 'active' : ''}" data-filter="all">全部</button>
          <button type="button" class="filter-chip ${currentFindingFilter === 'rule' ? 'active' : ''}" data-filter="rule">规则</button>
          <button type="button" class="filter-chip ${currentFindingFilter === 'llm' ? 'active' : ''}" data-filter="llm">模型新增</button>
        </div>`;
      issuesListNode.innerHTML = filtered.length
        ? filtered.map((finding, index) => renderIssueItem(finding, index + 1)).join('')
        : '<div class="empty">当前没有识别出需要提示的问题。</div>';
      issuesHeadNode.querySelectorAll('.filter-chip').forEach((node) => {
        node.addEventListener('click', () => {
          currentFindingFilter = node.dataset.filter;
          renderIssues(latestFindings);
        });
      });
      issuesListNode.querySelectorAll('.issue-summary').forEach((node) => {
        node.addEventListener('click', () => {
          const card = node.closest('.issue-item');
          selectFinding(card.dataset.findingId);
        });
      });
      issuesListNode.querySelectorAll('.issue-locate-btn').forEach((node) => {
        node.addEventListener('click', (event) => {
          event.stopPropagation();
          const card = node.closest('.issue-item');
          selectFinding(card.dataset.findingId);
        });
      });
      issuesListNode.querySelectorAll('.issue-toggle-btn').forEach((node) => {
        node.addEventListener('click', (event) => {
          event.stopPropagation();
          const card = node.closest('.issue-item');
          card.classList.toggle('expanded');
          node.querySelector('.issue-toggle-text').textContent = card.classList.contains('expanded') ? '收起详情' : '展开详情';
        });
      });
      workspaceNode.style.display = 'grid';
    }

    function renderIssueItem(finding, index) {
      const originLabel = finding.finding_origin === 'llm_added' ? '模型新增' : '规则命中';
      const originClass = finding.finding_origin === 'llm_added' ? 'origin-llm' : 'origin-rule';
      return `<article class="issue-item ${escapeHtml(finding.risk_level || '')}" data-finding-id="${escapeHtml(finding.finding_id)}">
        <button type="button" class="issue-summary">
          <div class="issue-top">
            <span>问题 ${index}</span>
            <span class="badge ${escapeHtml(finding.risk_level)}">${escapeHtml(riskLabel(finding.risk_level))}</span>
            <span class="badge">${escapeHtml(finding.issue_type)}</span>
            <span class="badge ${originClass}">${originLabel}</span>
          </div>
          <div class="issue-title-row">
            <div class="issue-rank ${escapeHtml(finding.risk_level || '')}">${String(index).padStart(2, '0')}</div>
            <div class="issue-main">
              <div class="issue-title">${escapeHtml(finding.problem_title)}</div>
              <div class="issue-meta">位置：${escapeHtml(finding.section_path || finding.source_section || '待补充')}</div>
              <div class="issue-meta">页码：${escapeHtml(finding.page_hint || '待人工翻页复核')} ｜ 行号：${escapeHtml(formatLineRange(finding.text_line_start, finding.text_line_end))}</div>
            </div>
          </div>
          <div class="issue-snippet">${escapeHtml(finding.source_text)}</div>
          <div class="issue-actions">
            <div class="issue-action-buttons">
              <button type="button" class="issue-mini-btn issue-locate-btn">定位正文</button>
              <button type="button" class="issue-mini-btn issue-toggle-btn"><span class="issue-toggle-text">展开详情</span></button>
            </div>
          </div>
        </button>
        <div class="issue-detail">
          <div class="detail-grid">
            <div class="detail-pair">
              <div class="detail-label">合规判断</div>
              <div class="detail-value">${escapeHtml(finding.compliance_judgment)}</div>
            </div>
            <div class="detail-pair">
              <div class="detail-label">来源</div>
              <div class="detail-value">${escapeHtml(originLabel)}</div>
            </div>
            <div class="detail-pair">
              <div class="detail-label">条款编号</div>
              <div class="detail-value">${escapeHtml(finding.clause_id || '待补充')}</div>
            </div>
            <div class="detail-pair">
              <div class="detail-label">表格/评分项</div>
              <div class="detail-value">${escapeHtml(finding.table_or_item_label || '—')}</div>
            </div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">风险说明</div>
            <div class="detail-value">${escapeHtml(finding.why_it_is_risky)}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">依据</div>
            <div class="detail-value">${escapeHtml(finding.legal_or_policy_basis || '当前离线链路未单独拆出更细依据，请结合正式审查结果复核。')}</div>
          </div>
          <div class="detail-pair">
            <div class="detail-label">修改建议</div>
            <div class="detail-value">${escapeHtml(finding.rewrite_suggestion)}</div>
          </div>
        </div>
      </article>`;
    }

    function renderDocument(documentPayload) {
      documentHeadNode.innerHTML = `
        <h2>文件正文</h2>
        <div class="meta">原文件：${escapeHtml(documentPayload.source_path)}</div>
        <div class="meta">稳定文本：${escapeHtml(documentPayload.normalized_text_path)}</div>
        <div class="meta">总行数：${documentPayload.line_count} ｜ 渲染模式：${documentPayload.render_mode === 'docx_blocks' ? 'DOCX 原文结构' : '稳定文本'}</div>`;
      documentBodyNode.innerHTML = documentPayload.render_mode === 'docx_blocks'
        ? documentPayload.blocks.map((block) => renderDocumentBlock(block)).join('')
        : documentPayload.lines.map((line) => renderDocumentLine(line)).join('');
      workspaceNode.style.display = 'grid';
    }

    function renderDocumentBlock(block) {
      const meta = `行号：${formatLineRange(block.start_line, block.end_line)}`;
      return `<div class="doc-block" id="${escapeHtml(block.block_id)}" data-start-line="${block.start_line}" data-end-line="${block.end_line}">
        ${block.html}
        <div class="doc-block-meta">${escapeHtml(meta)}</div>
      </div>`;
    }

    function renderDocumentLine(line) {
      return `<div class="doc-line" id="doc-line-${line.number}">
        <div class="doc-line-number">${String(line.number).padStart(4, '0')}${line.page_hint ? `<br>${escapeHtml(line.page_hint)}` : ''}</div>
        <div class="doc-line-text">${escapeHtml(line.text || ' ')}</div>
      </div>`;
    }

    function selectFinding(findingId) {
      const finding = latestFindings.find((item) => item.finding_id === findingId);
      if (!finding) return;
      issuesListNode.querySelectorAll('.issue-item').forEach((node) => {
        node.classList.toggle('active', node.dataset.findingId === findingId);
      });
      highlightDocumentRange(finding.text_line_start, finding.text_line_end);
    }

    function highlightDocumentRange(start, end) {
      documentBodyNode.querySelectorAll('.active').forEach((node) => node.classList.remove('active'));
      let target = null;
      if (latestDocument && latestDocument.render_mode === 'docx_blocks') {
        documentBodyNode.querySelectorAll('.doc-block').forEach((node) => {
          const blockStart = Number(node.dataset.startLine);
          const blockEnd = Number(node.dataset.endLine);
          const overlaps = blockStart <= end && blockEnd >= start;
          if (overlaps) {
            node.classList.add('active');
            if (!target) target = node;
          }
        });
      } else {
        for (let line = start; line <= end; line += 1) {
          const node = document.getElementById(`doc-line-${line}`);
          if (node) {
            node.classList.add('active');
            if (!target) target = node;
          }
        }
      }
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    async function openSourceFile() {
      if (!latestDocument || !latestDocument.source_path) return;
      try {
        const response = await fetch('/api/open-source', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: latestDocument.source_path }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || '打开失败');
      } catch (error) {
        statusNode.textContent = `打开原文件失败：${error.message}`;
      }
    }

    function formatLineRange(start, end) {
      if (!start && !end) return '—';
      if (!end || start === end) return String(start).padStart(4, '0');
      return `${String(start).padStart(4, '0')}-${String(end).padStart(4, '0')}`;
    }

    function riskLabel(level) {
      return ({ high: '高风险', medium: '中风险', low: '低风险' }[level] || level || '未标注');
    }

    function applyFindingFilter(findings, filter) {
      if (filter === 'llm') {
        return findings.filter((item) => item.finding_origin === 'llm_added');
      }
      if (filter === 'rule') {
        return findings.filter((item) => item.finding_origin !== 'llm_added');
      }
      return findings;
    }

    function sortFindings(findings) {
      const priority = { high: 0, medium: 1, low: 2, none: 3 };
      return [...findings].sort((left, right) => {
        const treatmentDiff = treatmentPriority(left).rank - treatmentPriority(right).rank;
        if (treatmentDiff !== 0) return treatmentDiff;
        const levelDiff = (priority[left.risk_level] ?? 9) - (priority[right.risk_level] ?? 9);
        if (levelDiff !== 0) return levelDiff;
        const lineDiff = (left.text_line_start || 0) - (right.text_line_start || 0);
        if (lineDiff !== 0) return lineDiff;
        return String(left.finding_id).localeCompare(String(right.finding_id));
      });
    }

    function escapeHtml(text) {
      return String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
  </script>
</body>
</html>"""


