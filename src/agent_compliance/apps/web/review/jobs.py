from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any

from agent_compliance.agents.compliance_review.pipelines.procurement_stage_router import route_procurement_stage


REVIEW_JOB_LOCK = threading.Lock()
REVIEW_JOBS: dict[str, dict[str, Any]] = {}
BUYER_PROGRESS_STEPS = (
    {"key": "parse", "label": "文档解析中", "description": "正在提取正文、章节和表格内容。"},
    {"key": "base_scan", "label": "基础风险扫描中", "description": "正在识别资格、评分、技术、商务/验收风险。"},
    {"key": "llm_enhance", "label": "智能增强分析中", "description": "正在补充边界问题、章节主问题和法规解释。"},
    {"key": "finalize", "label": "结果收束中", "description": "正在去重、合并主问题、整理证据和建议。"},
    {"key": "done", "label": "审查完成", "description": "可查看问题清单和导出结果。"},
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


def create_review_job(filename: str, source_path: Path, *, use_cache: bool, use_llm: bool, parser_mode: str) -> str:
    job_id = f"review-{uuid.uuid4().hex[:12]}"
    stage_profile = route_procurement_stage()
    now = time.time()
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
                "steps": [dict(item, status="pending") for item in BUYER_PROGRESS_STEPS],
                "technical_steps": [dict(item, status="pending") for item in BUYER_TECHNICAL_STEPS],
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


def mark_review_job(
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
        job["updated_at"] = time.time()


def review_job_status_payload(job_id: str) -> dict[str, Any] | None:
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


def review_job_result_payload(job_id: str) -> dict[str, Any] | None:
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


def _set_step_status(job: dict[str, Any], step_key: str, status: str) -> None:
    for step in job["progress"]["steps"]:
        if step["key"] == step_key:
            step["status"] = status
            break
    for step in job["progress"]["technical_steps"]:
        if step["key"] == step_key:
            step["status"] = status
            break
