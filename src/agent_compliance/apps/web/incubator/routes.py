from __future__ import annotations

import json
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from agent_compliance.core.config import detect_paths
from agent_compliance.incubator import (
    bootstrap_agent_factory,
    build_distillation_report,
    list_blueprints,
    load_incubation_run,
    resume_agent_factory,
    serialize_incubation_run,
    write_distillation_report,
    write_incubation_run,
)


def incubator_blueprints_payload() -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for blueprint in list_blueprints():
        payload.append(
            {
                "agent_key": blueprint.agent_key,
                "agent_name": blueprint.agent_name,
                "agent_type": blueprint.agent_type,
                "goal": blueprint.goal,
            }
        )
    return payload


def handle_incubator_start(handler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        agent_key = str(payload.get("agent_key", "")).strip()
        run_title = str(payload.get("run_title", "")).strip() or None
        resume_run = str(payload.get("resume_run", "")).strip() or None
        overwrite = bool(payload.get("overwrite", False))
        if not agent_key:
            handler._send_json({"error": "缺少 agent_key"}, status=HTTPStatus.BAD_REQUEST)
            return

        paths = detect_paths()
        agents_dir = paths.repo_root / "src" / "agent_compliance" / "agents"
        output_dir = paths.repo_root / "docs" / "generated" / "incubator"

        if resume_run:
            run_manifest_path = safe_incubator_path(resume_run, output_dir)
            run = load_incubation_run(run_manifest_path)
            if run.agent_key != agent_key:
                handler._send_json(
                    {"error": f"run manifest agent_key={run.agent_key} 与当前蓝图 {agent_key} 不一致"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            result = resume_agent_factory(run)
            run_key = run_key_from_manifest(run_manifest_path)
        else:
            result = bootstrap_agent_factory(
                agents_dir,
                agent_key,
                run_title=run_title,
                overwrite=overwrite,
            )
            run_key = slugify_run_key(result.run.run_title)

        artifact_paths = write_distillation_report(
            output_dir,
            result.blueprint.agent_key,
            run_key,
            result.report,
            result.report_markdown,
        )
        run_paths = write_incubation_run(
            output_dir,
            result.blueprint.agent_key,
            run_key,
            result.run,
        )
        handler._send_json(
            {
                "agent_key": result.blueprint.agent_key,
                "agent_name": result.blueprint.agent_name,
                "run_title": result.run.run_title,
                "outputs": {
                    "run_manifest": str(run_paths.manifest_path),
                    "report_json": str(artifact_paths.json_path),
                    "report_markdown": str(artifact_paths.markdown_path),
                },
                "summary": result.report["summary"],
            }
        )
    except Exception as exc:
        handler._send_json({"error": f"启动孵化失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def handle_incubator_run_detail(handler, query: str) -> None:
    params = parse_qs(query)
    requested_path = (params.get("path") or [""])[0]
    if not requested_path:
        handler._send_json({"error": "缺少 path"}, status=HTTPStatus.BAD_REQUEST)
        return
    try:
        paths = detect_paths()
        base_dir = paths.repo_root / "docs" / "generated" / "incubator"
        manifest_path = safe_incubator_path(requested_path, base_dir)
        run = load_incubation_run(manifest_path)
        run_key = run_key_from_manifest(manifest_path)
        report_markdown_path = manifest_path.parent / f"{run_key}-distillation-report.md"
        report_markdown = ""
        if report_markdown_path.exists():
            report_markdown = report_markdown_path.read_text(encoding="utf-8")
        handler._send_json(
            {
                "run_manifest": str(manifest_path),
                "agent_key": run.agent_key,
                "run_title": run.run_title,
                "report_markdown_path": str(report_markdown_path) if report_markdown_path.exists() else None,
                "report_markdown": report_markdown,
                "run": serialize_incubation_run(run),
            }
        )
    except Exception as exc:
        handler._send_json({"error": f"读取 run 详情失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def list_incubator_runs() -> list[dict[str, Any]]:
    base_dir = detect_paths().repo_root / "docs" / "generated" / "incubator"
    if not base_dir.exists():
        return []
    runs: list[dict[str, Any]] = []
    for manifest_path in sorted(base_dir.rglob("*-run.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            run = load_incubation_run(manifest_path)
        except Exception:
            continue
        run_key = run_key_from_manifest(manifest_path)
        report_markdown_path = manifest_path.parent / f"{run_key}-distillation-report.md"
        report_json_path = manifest_path.parent / f"{run_key}-distillation-report.json"
        report_summary = build_distillation_report(run)["summary"]
        runs.append(
            {
                "agent_key": run.agent_key,
                "run_title": run.run_title,
                "run_manifest": str(manifest_path),
                "report_markdown": str(report_markdown_path) if report_markdown_path.exists() else None,
                "report_json": str(report_json_path) if report_json_path.exists() else None,
                "updated_at": datetime.fromtimestamp(manifest_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "summary": report_summary,
            }
        )
    return runs


def slugify_run_key(run_title: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    normalized = "".join(
        char if char.isalnum() or char in ("-", "_") else "-"
        for char in run_title.lower()
    )
    normalized = "-".join(part for part in normalized.split("-") if part)
    return f"{timestamp}-{normalized or 'incubation-run'}"


def run_key_from_manifest(path: Path) -> str:
    if path.name.endswith("-run.json"):
        return path.name[: -len("-run.json")]
    return path.stem


def safe_incubator_path(requested_path: str, base_dir: Path) -> Path:
    candidate = Path(requested_path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    resolved = candidate.resolve()
    resolved.relative_to(base_dir.resolve())
    return resolved
