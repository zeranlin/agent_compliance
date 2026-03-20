from __future__ import annotations

from agent_compliance.incubator.blueprints.base import AgentBlueprint, create_agent_blueprint
from agent_compliance.incubator.blueprints.type_templates import BUDGET_ANALYSIS_AGENT_TEMPLATE


BUDGET_AGENT_BLUEPRINT = create_agent_blueprint(
    template=BUDGET_ANALYSIS_AGENT_TEMPLATE,
    agent_key="budget_demand",
    agent_name="政府采购预算需求智能体",
    goal=(
        "围绕政府采购预算需求形成与复核，识别预算测算依据、数量单价总价口径、"
        "预算范围、预算结构和预算漏重项等问题。"
    ),
    inputs=(
        "预算需求材料",
        "预算测算表",
        "预算依据附件",
        "正负样例",
        "人工预算复核基准",
    ),
    outputs=(
        "预算问题列表",
        "结构化 BudgetFindings",
        "预算依据缺口说明",
        "预算复核建议",
        "导出结果",
    ),
    incubation_focus=(
        "预算表结构解析",
        "数量单价总价一致性",
        "预算依据完整性",
        "预算范围与重复项识别",
    ),
)


def budget_agent_blueprint() -> AgentBlueprint:
    """返回政府采购预算需求智能体蓝图。"""

    return BUDGET_AGENT_BLUEPRINT
