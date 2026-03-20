from __future__ import annotations

from agent_compliance.incubator.blueprints.base import AgentBlueprint


DEMAND_RESEARCH_AGENT_BLUEPRINT = AgentBlueprint(
    agent_key="demand_research",
    agent_name="政府采购需求调查智能体",
    agent_type="demand_research_agent",
    goal=(
        "围绕政府采购需求调查与需求初稿形成，接收采购品目、预算和场景约束，"
        "输出结构完整、便于人工修改的采购需求初稿骨架。"
    ),
    inputs=(
        "采购品目",
        "预算金额",
        "采购场景与使用单位",
        "交付地点与周期",
        "正负样例",
        "人工需求调查基准",
    ),
    outputs=(
        "采购需求初稿",
        "结构化需求章节骨架",
        "待人工补充项",
        "需求调查问题清单",
        "导出结果",
    ),
    shared_capabilities=(
        "normalize",
        "tender_document_parser",
        "catalog classification",
        "legal authorities",
        "cache",
        "export base",
        "web shell",
    ),
    required_files=(
        "schemas.py",
        "pipeline.py",
        "service.py",
        "rules/__init__.py",
        "analyzers/__init__.py",
        "web/__init__.py",
    ),
    default_directories=("rules", "analyzers", "web"),
    incubation_focus=(
        "采购需求章节结构生成",
        "预算约束向需求条款转换",
        "品目驱动的需求初稿模板",
        "待人工补充项与边界提示",
    ),
)


def demand_research_agent_blueprint() -> AgentBlueprint:
    """返回政府采购需求调查智能体蓝图。"""

    return DEMAND_RESEARCH_AGENT_BLUEPRINT
