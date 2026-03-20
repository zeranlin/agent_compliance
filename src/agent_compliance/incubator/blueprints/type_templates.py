from __future__ import annotations

from agent_compliance.incubator.blueprints.base import AgentBlueprintTemplate


COMMON_SHARED_CAPABILITIES = (
    "normalize",
    "tender_document_parser",
    "catalog classification",
    "legal authorities",
    "cache",
    "export base",
    "web shell",
)

COMMON_REQUIRED_FILES = (
    "schemas.py",
    "pipeline.py",
    "service.py",
    "rules/__init__.py",
    "analyzers/__init__.py",
    "web/__init__.py",
)

COMMON_DIRECTORIES = ("rules", "analyzers", "web")


REVIEW_AGENT_TEMPLATE = AgentBlueprintTemplate(
    template_key="review",
    template_name="审查型智能体模板",
    agent_type="review_agent",
    default_inputs=(
        "业务文档",
        "正负样例",
        "人工审查基准",
    ),
    default_outputs=(
        "问题列表",
        "结构化 findings",
        "依据说明",
        "改写建议",
        "导出结果",
    ),
    shared_capabilities=COMMON_SHARED_CAPABILITIES,
    required_files=COMMON_REQUIRED_FILES,
    default_directories=COMMON_DIRECTORIES,
    incubation_focus=(
        "人工审查对照",
        "规则与 analyzer 主链设计",
        "仲裁与证据收束",
    ),
)

BUDGET_ANALYSIS_AGENT_TEMPLATE = AgentBlueprintTemplate(
    template_key="budget_analysis",
    template_name="预算分析型智能体模板",
    agent_type="budget_agent",
    default_inputs=(
        "预算需求材料",
        "预算测算表",
        "正负样例",
        "人工预算复核基准",
    ),
    default_outputs=(
        "预算问题列表",
        "结构化 findings",
        "预算说明",
        "导出结果",
    ),
    shared_capabilities=COMMON_SHARED_CAPABILITIES,
    required_files=COMMON_REQUIRED_FILES,
    default_directories=COMMON_DIRECTORIES,
    incubation_focus=(
        "预算表结构解析",
        "数量单价总价一致性",
        "预算依据完整性",
    ),
)

DEMAND_RESEARCH_AGENT_TEMPLATE = AgentBlueprintTemplate(
    template_key="demand_research",
    template_name="调研生成型智能体模板",
    agent_type="demand_research_agent",
    default_inputs=(
        "品目与预算输入",
        "场景约束",
        "正负样例",
        "人工调查基准",
    ),
    default_outputs=(
        "结构化初稿",
        "待补充项",
        "问题清单",
        "导出结果",
    ),
    shared_capabilities=COMMON_SHARED_CAPABILITIES,
    required_files=COMMON_REQUIRED_FILES,
    default_directories=COMMON_DIRECTORIES,
    incubation_focus=(
        "章节结构生成",
        "预算约束转条款",
        "待人工补充项组织",
    ),
)

COMPARISON_EVAL_AGENT_TEMPLATE = AgentBlueprintTemplate(
    template_key="comparison_eval",
    template_name="对比评估型智能体模板",
    agent_type="comparison_eval_agent",
    default_inputs=(
        "基线结果",
        "目标结果",
        "评分规则",
        "样例资产",
    ),
    default_outputs=(
        "差异清单",
        "评估结论",
        "增强建议",
        "导出结果",
    ),
    shared_capabilities=COMMON_SHARED_CAPABILITIES,
    required_files=COMMON_REQUIRED_FILES,
    default_directories=COMMON_DIRECTORIES,
    incubation_focus=(
        "差异采集",
        "评估口径统一",
        "增强建议收敛",
    ),
)

BLUEPRINT_TEMPLATE_REGISTRY: dict[str, AgentBlueprintTemplate] = {
    REVIEW_AGENT_TEMPLATE.template_key: REVIEW_AGENT_TEMPLATE,
    BUDGET_ANALYSIS_AGENT_TEMPLATE.template_key: BUDGET_ANALYSIS_AGENT_TEMPLATE,
    DEMAND_RESEARCH_AGENT_TEMPLATE.template_key: DEMAND_RESEARCH_AGENT_TEMPLATE,
    COMPARISON_EVAL_AGENT_TEMPLATE.template_key: COMPARISON_EVAL_AGENT_TEMPLATE,
}


def list_blueprint_templates() -> tuple[AgentBlueprintTemplate, ...]:
    """返回当前已注册的蓝图模板。"""

    return tuple(BLUEPRINT_TEMPLATE_REGISTRY.values())


def get_blueprint_template(template_key: str) -> AgentBlueprintTemplate:
    """按 template_key 获取标准蓝图模板。"""

    try:
        return BLUEPRINT_TEMPLATE_REGISTRY[template_key]
    except KeyError as exc:
        raise KeyError(f"Unknown blueprint template: {template_key}") from exc
