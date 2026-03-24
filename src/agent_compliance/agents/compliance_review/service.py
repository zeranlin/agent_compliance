from __future__ import annotations

from pathlib import Path

from agent_compliance.agents.compliance_review.pipeline import ComplianceReviewRunResult, run_pipeline
from agent_compliance.core.config import LLMConfig


def review(
    input_path: str | Path,
    *,
    use_cache: bool = False,
    refresh_cache: bool = False,
    llm_config: LLMConfig | None = None,
    parser_mode: str | None = None,
    output_stem: str | None = None,
    write_outputs: bool = True,
) -> dict[str, object]:
    """采购需求合规性检查智能体的稳定公共服务入口。"""

    return review_run(
        input_path,
        use_cache=use_cache,
        refresh_cache=refresh_cache,
        llm_config=llm_config,
        parser_mode=parser_mode,
        output_stem=output_stem,
        write_outputs=write_outputs,
    ).to_payload()


def review_run(
    input_path: str | Path,
    *,
    use_cache: bool = False,
    refresh_cache: bool = False,
    llm_config: LLMConfig | None = None,
    parser_mode: str | None = None,
    output_stem: str | None = None,
    write_outputs: bool = True,
) -> ComplianceReviewRunResult:
    """返回真实运行对象，供 CLI、Web 和后续 agent 统一复用。"""

    return run_pipeline(
        input_path,
        use_cache=use_cache,
        refresh_cache=refresh_cache,
        llm_config=llm_config,
        parser_mode=parser_mode,
        output_stem=output_stem,
        write_outputs=write_outputs,
    )
