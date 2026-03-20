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
    build_sample_manifest,
    build_validation_comparison,
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


def handle_incubator_continue(handler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        requested_path = str(payload.get("run_manifest", "")).strip()
        if not requested_path:
            handler._send_json({"error": "缺少 run_manifest"}, status=HTTPStatus.BAD_REQUEST)
            return

        paths = detect_paths()
        output_dir = paths.repo_root / "docs" / "generated" / "incubator"
        manifest_path = safe_incubator_path(requested_path, output_dir)
        run = load_incubation_run(manifest_path)

        sample_manifest = _build_sample_manifest_from_payload(payload)
        comparison = _build_comparison_from_payload(payload)
        if sample_manifest is None and comparison is None:
            handler._send_json(
                {"error": "至少需要补充一项：样例清单或三方对照文本"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        result = resume_agent_factory(
            run,
            sample_manifest=sample_manifest,
            comparisons=(comparison,) if comparison else (),
        )
        run_key = run_key_from_manifest(manifest_path)
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
                "continued": {
                    "sample_manifest_added": sample_manifest is not None,
                    "comparison_added": comparison is not None,
                },
            }
        )
    except Exception as exc:
        handler._send_json({"error": f"续跑孵化失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


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


def _split_lines(raw_value: Any) -> tuple[str, ...]:
    if not isinstance(raw_value, str):
        return ()
    return tuple(line.strip() for line in raw_value.splitlines() if line.strip())


def _build_sample_manifest_from_payload(payload: dict[str, Any]):
    positive_paths = _split_lines(payload.get("positive_paths"))
    negative_paths = _split_lines(payload.get("negative_paths"))
    boundary_paths = _split_lines(payload.get("boundary_paths"))
    if not any((positive_paths, negative_paths, boundary_paths)):
        return None
    manifest_name = str(payload.get("manifest_name", "")).strip() or "Web 补充样例"
    return build_sample_manifest(
        manifest_name,
        positive_paths=positive_paths,
        negative_paths=negative_paths,
        boundary_paths=boundary_paths,
    )


def _build_comparison_from_payload(payload: dict[str, Any]):
    sample_id = str(payload.get("comparison_sample_id", "")).strip()
    human_baseline = str(payload.get("human_baseline", "")).strip()
    strong_agent_result = str(payload.get("strong_agent_result", "")).strip()
    target_agent_result = str(payload.get("target_agent_result", "")).strip()
    comparison_summary = str(payload.get("comparison_summary", "")).strip()
    has_any = any((sample_id, human_baseline, strong_agent_result, target_agent_result, comparison_summary))
    if not has_any:
        return None
    if not (sample_id and human_baseline and strong_agent_result and target_agent_result):
        raise ValueError("三方对照需同时提供样例 ID、人工基准、强通用智能体结果和目标智能体结果")
    return build_validation_comparison(
        sample_id=sample_id,
        human_baseline=human_baseline,
        strong_agent_result=strong_agent_result,
        target_agent_result=target_agent_result,
        summary=comparison_summary,
    )
