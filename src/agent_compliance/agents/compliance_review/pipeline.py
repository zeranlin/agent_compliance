from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_compliance.agents.compliance_review.pipelines.llm_enhance import enhance_review_result
from agent_compliance.agents.compliance_review.pipelines.llm_review import LLMReviewArtifacts, apply_llm_review_tasks
from agent_compliance.agents.compliance_review.pipelines.render import write_review_outputs
from agent_compliance.agents.compliance_review.pipelines.review import build_review_result
from agent_compliance.agents.compliance_review.pipelines.rule_scan import run_rule_scan
from agent_compliance.agents.compliance_review.rules.base import RULE_SET_VERSION
from agent_compliance.core.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.core.config import LLMConfig, detect_llm_config, detect_paths, detect_tender_parser_mode
from agent_compliance.core.pipelines.normalize import run_normalize
from agent_compliance.core.schemas import NormalizedDocument, ReviewResult


@dataclass(frozen=True)
class ComplianceReviewRunResult:
    """统一描述一次采购需求合规性检查智能体执行结果。"""

    normalized: NormalizedDocument
    review: ReviewResult
    llm_artifacts: LLMReviewArtifacts
    cache_enabled: bool
    cache_used: bool
    cache_key: str
    parser_mode: str
    llm_config: LLMConfig
    json_path: Path | None = None
    markdown_path: Path | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "review": self.review.to_dict(),
            "cache": {
                "enabled": self.cache_enabled,
                "used": self.cache_used,
                "key": self.cache_key,
            },
            "llm": {
                "enabled": self.llm_config.enabled,
                "base_url": self.llm_config.base_url,
                "model": self.llm_config.model,
            },
            "parser": {"mode": self.parser_mode, "enabled": self.parser_mode != "off"},
            "llm_review": self.llm_artifacts.to_dict(),
            "outputs": {
                "json": str(self.json_path) if self.json_path else None,
                "markdown": str(self.markdown_path) if self.markdown_path else None,
            },
        }


def run_pipeline(
    input_path: str | Path,
    *,
    use_cache: bool = False,
    refresh_cache: bool = False,
    llm_config: LLMConfig | None = None,
    parser_mode: str | None = None,
    output_stem: str | None = None,
    write_outputs: bool = True,
) -> ComplianceReviewRunResult:
    """采购需求合规性检查智能体 的统一真实执行入口。"""

    paths = detect_paths()
    normalized = run_normalize(Path(input_path))
    resolved_parser_mode = parser_mode or detect_tender_parser_mode()
    resolved_llm_config = llm_config or detect_llm_config()

    reference_snapshot = reference_snapshot_id(paths.repo_root / "docs" / "references")
    cache_key = build_review_cache_key(
        file_hash=normalized.file_hash,
        rule_set_version=RULE_SET_VERSION,
        reference_snapshot=reference_snapshot,
        parser_mode=resolved_parser_mode,
        review_pipeline_version=REVIEW_CACHE_VERSION,
    )
    review = None
    cache_used = False
    if use_cache and not refresh_cache:
        review = load_review_cache(cache_key)
        cache_used = review is not None
    if review is None:
        hits = run_rule_scan(normalized)
        review = build_review_result(normalized, hits, parser_mode=resolved_parser_mode)
        if use_cache:
            save_review_cache(
                cache_key,
                review,
                metadata={
                    "file_hash": normalized.file_hash,
                    "rule_set_version": RULE_SET_VERSION,
                    "reference_snapshot": reference_snapshot,
                    "parser_mode": resolved_parser_mode,
                    "review_pipeline_version": REVIEW_CACHE_VERSION,
                },
            )

    review = enhance_review_result(review, resolved_llm_config)
    artifact_stem = output_stem or normalized.file_hash[:12]
    review, llm_artifacts = apply_llm_review_tasks(
        normalized,
        review,
        resolved_llm_config,
        output_stem=artifact_stem,
    )

    json_path = None
    markdown_path = None
    if write_outputs:
        json_path, markdown_path = write_review_outputs(review, artifact_stem)

    return ComplianceReviewRunResult(
        normalized=normalized,
        review=review,
        llm_artifacts=llm_artifacts,
        cache_enabled=use_cache,
        cache_used=cache_used,
        cache_key=cache_key,
        parser_mode=resolved_parser_mode,
        llm_config=resolved_llm_config,
        json_path=json_path,
        markdown_path=markdown_path,
    )
