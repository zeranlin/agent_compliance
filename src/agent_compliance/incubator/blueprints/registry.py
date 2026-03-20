from __future__ import annotations

from agent_compliance.incubator.blueprints.base import AgentBlueprint
from agent_compliance.incubator.blueprints.budget_agent import BUDGET_AGENT_BLUEPRINT
from agent_compliance.incubator.blueprints.demand_research_agent import (
    DEMAND_RESEARCH_AGENT_BLUEPRINT,
)
from agent_compliance.incubator.blueprints.review_agent import REVIEW_AGENT_BLUEPRINT
from agent_compliance.incubator.blueprints.special_checks_agent import (
    SPECIAL_CHECKS_AGENT_BLUEPRINT,
)


BLUEPRINT_REGISTRY: dict[str, AgentBlueprint] = {
    REVIEW_AGENT_BLUEPRINT.agent_key: REVIEW_AGENT_BLUEPRINT,
    BUDGET_AGENT_BLUEPRINT.agent_key: BUDGET_AGENT_BLUEPRINT,
    DEMAND_RESEARCH_AGENT_BLUEPRINT.agent_key: DEMAND_RESEARCH_AGENT_BLUEPRINT,
    SPECIAL_CHECKS_AGENT_BLUEPRINT.agent_key: SPECIAL_CHECKS_AGENT_BLUEPRINT,
}


def list_blueprints() -> tuple[AgentBlueprint, ...]:
    """返回当前已注册的标准蓝图。"""

    return tuple(BLUEPRINT_REGISTRY.values())


def get_blueprint(agent_key: str) -> AgentBlueprint:
    """按 agent_key 获取标准蓝图。"""

    try:
        return BLUEPRINT_REGISTRY[agent_key]
    except KeyError as exc:
        raise KeyError(f"Unknown blueprint: {agent_key}") from exc
