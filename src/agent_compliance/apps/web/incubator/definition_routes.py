from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from agent_compliance.core.config import detect_paths
from agent_compliance.incubator import (
    build_requirement_definition,
    build_requirement_guidance,
    get_blueprint_template,
    list_blueprint_templates,
    write_requirement_definition,
)


def incubator_template_payload() -> list[dict[str, str]]:
    return [
        {
            "template_key": template.template_key,
            "template_name": template.template_name,
            "agent_type": template.agent_type,
        }
        for template in list_blueprint_templates()
    ]


def handle_requirement_definition_submit(handler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        action = str(payload.get("action", "analyze")).strip() or "analyze"
        if action == "analyze":
            _handle_requirement_definition_analyze(handler, payload)
            return
        if action == "generate":
            _handle_requirement_definition_generate(handler, payload)
            return
        handler._send_json({"error": f"不支持的 action：{action}"}, status=HTTPStatus.BAD_REQUEST)
    except Exception as exc:
        handler._send_json({"error": f"处理需求定义请求失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def _handle_requirement_definition_analyze(handler, payload: dict[str, Any]) -> None:
    guidance = build_requirement_guidance(
        agent_name=str(payload.get("agent_name", "")).strip(),
        business_need=str(payload.get("business_need", "")).strip(),
        usage_scenario=str(payload.get("usage_scenario", "")).strip(),
    )
    handler._send_json(
        {
            "guidance": {
                "agent_name": guidance.agent_name,
                "template_key": guidance.template_key,
                "template_name": guidance.template_name,
                "product_direction": guidance.product_direction,
                "handling_process": list(guidance.handling_process),
                "clarification_questions": list(guidance.clarification_questions),
                "suggested_user_roles": list(guidance.suggested_user_roles),
                "suggested_input_documents": list(guidance.suggested_input_documents),
                "suggested_expected_outputs": list(guidance.suggested_expected_outputs),
                "suggested_success_criteria": list(guidance.suggested_success_criteria),
                "suggested_non_goals": list(guidance.suggested_non_goals),
            }
        }
    )


def _handle_requirement_definition_generate(handler, payload: dict[str, Any]) -> None:
    template_key = str(payload.get("template_key", "")).strip()
    if not template_key:
        guidance = build_requirement_guidance(
            agent_name=str(payload.get("agent_name", "")).strip(),
            business_need=str(payload.get("business_need", "")).strip(),
            usage_scenario=str(payload.get("usage_scenario", "")).strip(),
        )
        template_key = guidance.template_key
    template = get_blueprint_template(template_key)
    draft = build_requirement_definition(
        agent_name=str(payload.get("agent_name", "")).strip(),
        template_key=template.template_key,
        business_need=str(payload.get("business_need", "")).strip(),
        usage_scenario=str(payload.get("usage_scenario", "")).strip(),
        user_roles=_split_lines(payload.get("user_roles")),
        input_documents=_split_lines(payload.get("input_documents")),
        expected_outputs=_split_lines(payload.get("expected_outputs")),
        success_criteria=_split_lines(payload.get("success_criteria")),
        non_goals=_split_lines(payload.get("non_goals")),
        constraints=_split_lines(payload.get("constraints")),
    )
    output_dir = detect_paths().repo_root / "docs" / "generated" / "incubator-definition"
    artifact_paths = write_requirement_definition(output_dir, draft)
    handler._send_json(
        {
            "draft": {
                "agent_name": draft.agent_name,
                "template_key": draft.template_key,
                "product_definition": draft.product_definition,
                "capability_boundary": list(draft.capability_boundary),
                "first_version_goal": draft.first_version_goal,
            },
            "outputs": {
                "json": str(artifact_paths.json_path),
                "markdown": str(artifact_paths.markdown_path),
            },
            "preview_markdown": artifact_paths.markdown_path.read_text(encoding="utf-8"),
        }
    )


def _split_lines(raw_value: Any) -> tuple[str, ...]:
    if not isinstance(raw_value, str):
        return ()
    return tuple(line.strip() for line in raw_value.splitlines() if line.strip())


__all__ = [
    "handle_requirement_definition_submit",
    "incubator_template_payload",
]
