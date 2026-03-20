from __future__ import annotations

from agent_compliance.incubator.blueprints.base import AgentBlueprint


REVIEW_AGENT_BLUEPRINT = AgentBlueprint(
    agent_key="compliance_review",
    agent_name="采购需求合规性检查智能体",
    agent_type="review_agent",
    goal=(
        "围绕采购需求形成、复核和发布前审查，识别资格、评分、技术、"
        "商务/验收等条款中的结构性风险，并输出可直接用于改稿和复核的结果。"
    ),
    inputs=(
        "采购需求文本",
        "招标文件/磋商文件/征集文件",
        "正负样例",
        "人工审查基准",
    ),
    outputs=(
        "主问题列表",
        "结构化 findings",
        "法规依据",
        "建议改写",
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
        "人工审查对照",
        "规则与 analyzer 主链设计",
        "仲裁与证据收束",
        "发布前风险识别准确率",
    ),
)


def review_agent_blueprint() -> AgentBlueprint:
    """返回采购需求合规性检查智能体蓝图。"""

    return REVIEW_AGENT_BLUEPRINT
