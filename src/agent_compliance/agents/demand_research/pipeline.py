from __future__ import annotations


def run_pipeline(input_path: str) -> dict[str, object]:
    """政府采购需求调查智能体 的最小 pipeline 入口。"""

    return {
        "agent_key": "demand_research",
        "input_path": input_path,
        "status": "bootstrap",
    }
