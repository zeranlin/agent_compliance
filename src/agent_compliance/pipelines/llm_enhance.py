from __future__ import annotations

from copy import deepcopy

from agent_compliance.config import LLMConfig
from agent_compliance.models.llm_client import ChatMessage, OpenAICompatibleLLMClient
from agent_compliance.schemas import ReviewResult


SYSTEM_PROMPT = (
    "你是政府采购合规审查助手。"
    "你只对已有 finding 做轻量润色，不新增、不删除风险结论。"
    "输出必须是 JSON 数组，每项仅包含 finding_id、problem_title、why_it_is_risky、rewrite_suggestion。"
)


def enhance_review_result(review: ReviewResult, llm_config: LLMConfig) -> ReviewResult:
    if not llm_config.enabled:
        return review

    client = OpenAICompatibleLLMClient(llm_config)
    targets = [finding for finding in review.findings if finding.needs_human_review or "已合并" in finding.problem_title]
    if not targets:
        return review

    prompt = _build_prompt(review.document_name, targets)
    try:
        content = client.chat(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=prompt),
            ]
        )
        return _apply_enhancements(review, content)
    except Exception:
        return review


def _build_prompt(document_name: str, targets) -> str:
    lines = [
        f"文件：{document_name}",
        "请仅润色以下 finding 的问题标题、风险说明、修改建议，保持结论不变：",
    ]
    for finding in targets:
        lines.extend(
            [
                f"- finding_id: {finding.finding_id}",
                f"  issue_type: {finding.issue_type}",
                f"  problem_title: {finding.problem_title}",
                f"  source_text: {finding.source_text}",
                f"  why_it_is_risky: {finding.why_it_is_risky}",
                f"  rewrite_suggestion: {finding.rewrite_suggestion}",
            ]
        )
    return "\n".join(lines)


def _apply_enhancements(review: ReviewResult, content: str) -> ReviewResult:
    import json

    payload = json.loads(content)
    updates = {item["finding_id"]: item for item in payload}
    result = deepcopy(review)
    for finding in result.findings:
        update = updates.get(finding.finding_id)
        if not update:
            continue
        finding.problem_title = update.get("problem_title", finding.problem_title)
        finding.why_it_is_risky = update.get("why_it_is_risky", finding.why_it_is_risky)
        finding.rewrite_suggestion = update.get("rewrite_suggestion", finding.rewrite_suggestion)
    return result
