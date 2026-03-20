from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RequirementDefinitionDraft:
    """描述第一层需求定义阶段产出的业务蓝图确认稿。"""

    agent_name: str
    template_key: str
    business_need: str
    usage_scenario: str
    user_roles: tuple[str, ...]
    input_documents: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    success_criteria: tuple[str, ...]
    non_goals: tuple[str, ...]
    constraints: tuple[str, ...]
    product_definition: str
    capability_boundary: tuple[str, ...]
    first_version_goal: str


@dataclass(frozen=True)
class RequirementDefinitionPaths:
    """描述需求定义确认稿的落盘路径。"""

    target_dir: Path
    json_path: Path
    markdown_path: Path


def build_requirement_definition(
    *,
    agent_name: str,
    template_key: str,
    business_need: str,
    usage_scenario: str,
    user_roles: tuple[str, ...],
    input_documents: tuple[str, ...],
    expected_outputs: tuple[str, ...],
    success_criteria: tuple[str, ...],
    non_goals: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
) -> RequirementDefinitionDraft:
    """根据业务输入生成第一层需求定义确认稿。"""

    clean_agent_name = agent_name.strip()
    if not clean_agent_name:
        raise ValueError("缺少智能体名称")
    if not business_need.strip():
        raise ValueError("缺少业务需求描述")
    if not usage_scenario.strip():
        raise ValueError("缺少使用场景")
    if not user_roles:
        raise ValueError("至少需要一个用户角色")
    if not input_documents:
        raise ValueError("至少需要一个输入文档或输入项")
    if not expected_outputs:
        raise ValueError("至少需要一个目标输出")
    if not success_criteria:
        raise ValueError("至少需要一个成功标准")

    product_definition = (
        f"{clean_agent_name}面向{ '、'.join(user_roles) }，用于在“{usage_scenario.strip()}”场景下处理"
        f"{business_need.strip()}，并稳定输出{ '、'.join(expected_outputs) }。"
    )
    capability_boundary = (
        f"输入边界：当前第一版只处理 { '、'.join(input_documents) }。",
        f"输出边界：当前第一版只承诺输出 { '、'.join(expected_outputs) }。",
        f"使用边界：当前主要服务 { '、'.join(user_roles) }，不默认扩展到其他角色。",
        f"约束边界：{ '；'.join(constraints) if constraints else '当前以人工确认、样例驱动和可复核输出为主要约束。' }",
    )
    first_version_goal = (
        f"第一版先做到：围绕{business_need.strip()}，在 {usage_scenario.strip()} 场景下，"
        f"能稳定给 { '、'.join(user_roles) } 输出 { '、'.join(expected_outputs[:3]) }"
        f"{' 等结果' if len(expected_outputs) > 3 else ''}，并满足 {success_criteria[0]}。"
    )
    return RequirementDefinitionDraft(
        agent_name=clean_agent_name,
        template_key=template_key,
        business_need=business_need.strip(),
        usage_scenario=usage_scenario.strip(),
        user_roles=user_roles,
        input_documents=input_documents,
        expected_outputs=expected_outputs,
        success_criteria=success_criteria,
        non_goals=non_goals,
        constraints=constraints,
        product_definition=product_definition,
        capability_boundary=capability_boundary,
        first_version_goal=first_version_goal,
    )


def render_requirement_definition_markdown(draft: RequirementDefinitionDraft) -> str:
    """把需求定义确认稿渲染成 Markdown。"""

    lines = [
        f"# {draft.agent_name} 需求定义确认稿",
        "",
        f"- 模板类型：`{draft.template_key}`",
        "",
        "## 产品定义",
        "",
        draft.product_definition,
        "",
        "## 业务需求",
        "",
        draft.business_need,
        "",
        "## 使用场景",
        "",
        draft.usage_scenario,
        "",
        "## 用户角色",
        "",
    ]
    lines.extend([f"- {item}" for item in draft.user_roles])
    lines.extend(["", "## 输入", ""])
    lines.extend([f"- {item}" for item in draft.input_documents])
    lines.extend(["", "## 输出", ""])
    lines.extend([f"- {item}" for item in draft.expected_outputs])
    lines.extend(["", "## 成功标准", ""])
    lines.extend([f"- {item}" for item in draft.success_criteria])
    if draft.non_goals:
        lines.extend(["", "## 不做什么", ""])
        lines.extend([f"- {item}" for item in draft.non_goals])
    if draft.constraints:
        lines.extend(["", "## 约束条件", ""])
        lines.extend([f"- {item}" for item in draft.constraints])
    lines.extend(["", "## 能力边界", ""])
    lines.extend([f"- {item}" for item in draft.capability_boundary])
    lines.extend(["", "## 第一版目标", "", draft.first_version_goal, ""])
    return "\n".join(lines)


def write_requirement_definition(
    output_dir: Path,
    draft: RequirementDefinitionDraft,
) -> RequirementDefinitionPaths:
    """把需求定义确认稿写成标准 JSON 和 Markdown 产物。"""

    target_dir = output_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    definition_key = _definition_key(draft.agent_name)
    json_path = target_dir / f"{definition_key}-requirement-definition.json"
    markdown_path = target_dir / f"{definition_key}-requirement-definition.md"
    json_path.write_text(json.dumps(asdict(draft), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_requirement_definition_markdown(draft), encoding="utf-8")
    return RequirementDefinitionPaths(
        target_dir=target_dir,
        json_path=json_path,
        markdown_path=markdown_path,
    )


def _definition_key(agent_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    normalized = "".join(
        char if char.isalnum() or char in ("-", "_") else "-"
        for char in agent_name.lower()
    )
    normalized = "-".join(part for part in normalized.split("-") if part)
    return f"{timestamp}-{normalized or 'agent-definition'}"


__all__ = [
    "RequirementDefinitionDraft",
    "RequirementDefinitionPaths",
    "build_requirement_definition",
    "render_requirement_definition_markdown",
    "write_requirement_definition",
]
