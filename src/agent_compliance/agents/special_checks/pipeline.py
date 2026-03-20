from __future__ import annotations


def run_pipeline(input_path: str) -> dict[str, object]:
    """政府采购四类专项检查智能体 的最小 pipeline 入口。"""

    return {
        "agent_key": "special_checks",
        "input_path": input_path,
        "status": "bootstrap",
    }
