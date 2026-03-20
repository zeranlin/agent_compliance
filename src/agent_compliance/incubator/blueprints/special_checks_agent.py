from __future__ import annotations

from agent_compliance.incubator.blueprints.base import AgentBlueprint, create_agent_blueprint
from agent_compliance.incubator.blueprints.type_templates import REVIEW_AGENT_TEMPLATE


SPECIAL_CHECKS_AGENT_BLUEPRINT = create_agent_blueprint(
    template=REVIEW_AGENT_TEMPLATE,
    agent_key="special_checks",
    agent_name="政府采购四类专项检查智能体",
    goal=(
        "围绕政府采购文件中的四类专项检查事项，形成专项结论、定位证据、"
        "风险说明和整改建议，帮助采购人与复核人员快速完成专项核查。"
    ),
    inputs=(
        "采购文件或采购需求文本",
        "四类专项检查规则口径",
        "正负样例",
        "人工专项检查基准",
    ),
    outputs=(
        "四类专项检查结论",
        "专项问题列表",
        "结构化 findings",
        "整改建议",
        "导出结果",
    ),
    incubation_focus=(
        "四类专项检查结构固化",
        "专项结论模板统一",
        "证据定位与整改建议收束",
        "人工专项检查对照",
    ),
)


def special_checks_agent_blueprint() -> AgentBlueprint:
    """返回政府采购四类专项检查智能体蓝图。"""

    return SPECIAL_CHECKS_AGENT_BLUEPRINT
