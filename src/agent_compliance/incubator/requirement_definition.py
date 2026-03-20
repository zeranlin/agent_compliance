from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from agent_compliance.incubator.blueprints import get_blueprint_template


@dataclass(frozen=True)
class RequirementDefinitionGuidance:
    """描述第一层需求定义阶段的引导分析结果。"""

    agent_name: str
    business_need: str
    usage_scenario: str
    template_key: str
    template_name: str
    product_direction: str
    handling_process: tuple[str, ...]
    clarification_questions: tuple[str, ...]
    suggested_user_roles: tuple[str, ...]
    suggested_input_documents: tuple[str, ...]
    suggested_expected_outputs: tuple[str, ...]
    suggested_success_criteria: tuple[str, ...]
    suggested_non_goals: tuple[str, ...]


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


def infer_template_key(*, business_need: str, usage_scenario: str = "") -> str:
    """根据业务需求和使用场景推断蓝图模板。"""

    text = f"{business_need} {usage_scenario}".lower()
    if any(keyword in text for keyword in ("预算", "单价", "总价", "测算", "金额")):
        return "budget_analysis"
    if any(keyword in text for keyword in ("生成", "草稿", "初稿", "调研", "起草", "编制")):
        return "demand_research"
    if any(keyword in text for keyword in ("对比", "比较", "评估", "差异", "基线")):
        return "comparison_eval"
    return "review"


def build_requirement_guidance(
    *,
    agent_name: str,
    business_need: str,
    usage_scenario: str = "",
) -> RequirementDefinitionGuidance:
    """先把模糊业务需求转换成“处理流程 + 待补充问题 + 建议默认项”。"""

    clean_business_need = business_need.strip()
    if not clean_business_need:
        raise ValueError("缺少业务需求描述")
    clean_usage_scenario = usage_scenario.strip() or "实际业务执行场景待进一步确认"
    inferred_key = infer_template_key(
        business_need=clean_business_need,
        usage_scenario=clean_usage_scenario,
    )
    template = get_blueprint_template(inferred_key)
    clean_agent_name = agent_name.strip() or _default_agent_name(inferred_key)
    product_direction = (
        f"系统判断这更接近“{template.template_name}”，"
        f"建议先按{template.agent_type}路线孵化，再根据样例校正主链。"
    )
    handling_process = (
        "1. 需求定义：先确认业务目标、使用场景、用户角色、输入、输出和成功标准。",
        "2. 样例资产：准备正样例、负样例、边界样例和人工基准，形成可复用样例清单。",
        f"3. 强智能体设计：按 {template.template_name} 设计主链、schema、rules、analyzers 和评测方式。",
        "4. 本地智能体生成：按蓝图生成本地目标智能体骨架、默认测试、产品说明和评测占位。",
        "5. 对照蒸馏：用人工基准、强智能体和目标智能体三方对照，定位缺口并生成蒸馏建议。",
        "6. 固化发布：当结果稳定后，固化规则、schema、导出、benchmark 和产品化模板。",
    )
    clarification_questions = (
        "这个智能体的直接使用人是谁，谁会拿它的结果做下一步动作？",
        "它最常处理的输入材料是什么，哪些输入是必须有的？",
        "第一版最想稳定输出的 1 到 3 个结果是什么？",
        "什么错误最不能接受，哪些事情明确先不做？",
        "什么情况下你会认为第一版已经能试用了？",
    )
    return RequirementDefinitionGuidance(
        agent_name=clean_agent_name,
        business_need=clean_business_need,
        usage_scenario=clean_usage_scenario,
        template_key=template.template_key,
        template_name=template.template_name,
        product_direction=product_direction,
        handling_process=handling_process,
        clarification_questions=clarification_questions,
        suggested_user_roles=_suggested_user_roles(inferred_key),
        suggested_input_documents=template.default_inputs,
        suggested_expected_outputs=template.default_outputs,
        suggested_success_criteria=_suggested_success_criteria(inferred_key),
        suggested_non_goals=_suggested_non_goals(inferred_key),
    )


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
        f"{clean_agent_name}面向{'、'.join(user_roles)}，用于在“{usage_scenario.strip()}”场景下处理"
        f"{business_need.strip()}，并稳定输出{'、'.join(expected_outputs)}。"
    )
    capability_boundary = (
        f"输入边界：当前第一版只处理 {'、'.join(input_documents)}。",
        f"输出边界：当前第一版只承诺输出 {'、'.join(expected_outputs)}。",
        f"使用边界：当前主要服务 {'、'.join(user_roles)}，不默认扩展到其他角色。",
        f"约束边界：{'；'.join(constraints) if constraints else '当前以人工确认、样例驱动和可复核输出为主要约束。'}",
    )
    first_version_goal = (
        f"第一版先做到：围绕{business_need.strip()}，在 {usage_scenario.strip()} 场景下，"
        f"能稳定给 {'、'.join(user_roles)} 输出 {'、'.join(expected_outputs[:3])}"
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


def _default_agent_name(template_key: str) -> str:
    return {
        "review": "政府采购合规性检查智能体",
        "budget_analysis": "政府采购预算需求智能体",
        "demand_research": "政府采购需求调查智能体",
        "comparison_eval": "政府采购对比评估智能体",
    }.get(template_key, "待命名智能体")


def _suggested_user_roles(template_key: str) -> tuple[str, ...]:
    mapping = {
        "review": ("采购人", "法务复核人员", "代理机构"),
        "budget_analysis": ("采购人", "预算管理人员", "财务复核人员"),
        "demand_research": ("采购人", "业务需求提出人", "法务复核人员"),
        "comparison_eval": ("产品负责人", "评测人员", "业务审核人"),
    }
    return mapping.get(template_key, ("业务负责人",))


def _suggested_success_criteria(template_key: str) -> tuple[str, ...]:
    mapping = {
        "review": ("能稳定输出主问题", "能带出证据位置", "结果可供人工改稿"),
        "budget_analysis": ("能识别数量单价总价问题", "能输出预算依据缺口", "结果可用于预算复核"),
        "demand_research": ("能输出结构化初稿", "能明确待补充项", "结果可供人工二次编辑"),
        "comparison_eval": ("能稳定输出差异点", "能形成统一评估结论", "结果可用于迭代决策"),
    }
    return mapping.get(template_key, ("能形成稳定第一版输出",))


def _suggested_non_goals(template_key: str) -> tuple[str, ...]:
    mapping = {
        "review": ("不直接替代正式裁判", "不自动代替法务签发"),
        "budget_analysis": ("不直接替代财务审批", "不自动生成最终预算批复"),
        "demand_research": ("不直接替代正式发文", "不自动跳过人工确认直接发布"),
        "comparison_eval": ("不代替最终管理决策", "不把单次对照结果直接视为正式结论"),
    }
    return mapping.get(template_key, ())


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
    "RequirementDefinitionGuidance",
    "RequirementDefinitionPaths",
    "build_requirement_definition",
    "build_requirement_guidance",
    "infer_template_key",
    "render_requirement_definition_markdown",
    "write_requirement_definition",
]
