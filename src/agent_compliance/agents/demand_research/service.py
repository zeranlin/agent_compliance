from __future__ import annotations

from agent_compliance.agents.demand_research.pipeline import run_pipeline


def review(input_path: str) -> dict[str, object]:
    """政府采购需求调查智能体 的最小 service 入口。"""

    return run_pipeline(input_path)
