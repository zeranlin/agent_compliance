from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from agent_compliance.config import LLMConfig, detect_paths
from agent_compliance.evals.runner import benchmark_summary
from agent_compliance.models.llm_client import ChatMessage, OpenAICompatibleLLMClient
from agent_compliance.schemas import Clause, Finding, NormalizedDocument, ReviewResult


SYSTEM_PROMPT = (
    "你是政府采购需求审查智能体中的本地大模型推理层。"
    "你只处理给定任务，不做整篇自由发挥。"
    "如果条款问题不成立，返回 should_flag=false。"
    "输出必须是 JSON 对象，字段必须符合用户要求。"
)


@dataclass
class LLMReviewArtifacts:
    added_findings: list[Finding]
    rule_candidates: list[dict[str, object]]
    benchmark_gate: dict[str, object]
    candidate_json_path: str | None = None
    candidate_md_path: str | None = None
    benchmark_json_path: str | None = None
    benchmark_md_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "added_findings": [finding.to_dict() for finding in self.added_findings],
            "rule_candidates": self.rule_candidates,
            "benchmark_gate": self.benchmark_gate,
            "candidate_json_path": self.candidate_json_path,
            "candidate_md_path": self.candidate_md_path,
            "benchmark_json_path": self.benchmark_json_path,
            "benchmark_md_path": self.benchmark_md_path,
        }


def apply_llm_review_tasks(
    document: NormalizedDocument,
    review: ReviewResult,
    llm_config: LLMConfig,
    *,
    output_stem: str,
) -> tuple[ReviewResult, LLMReviewArtifacts]:
    empty = LLMReviewArtifacts(added_findings=[], rule_candidates=[], benchmark_gate={"status": "llm_disabled"})
    if not llm_config.enabled:
        return review, empty

    client = OpenAICompatibleLLMClient(llm_config)
    added_findings: list[Finding] = []
    added_findings.extend(_run_template_mismatch_task(document, review, client))
    added_findings.extend(_run_scoring_structure_task(document, review, client))
    added_findings.extend(_run_commercial_chain_task(document, review, client))

    merged_review = _merge_added_findings(review, added_findings)
    rule_candidates = generate_rule_candidates(document, merged_review, added_findings)
    benchmark_gate = run_benchmark_gate(rule_candidates)
    artifacts = write_improvement_outputs(output_stem, rule_candidates, benchmark_gate)
    artifacts.added_findings = added_findings
    artifacts.rule_candidates = rule_candidates
    artifacts.benchmark_gate = benchmark_gate
    return merged_review, artifacts


def generate_rule_candidates(
    document: NormalizedDocument,
    review: ReviewResult,
    added_findings: list[Finding],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for index, finding in enumerate(added_findings, start=1):
        clause = _clause_for_finding(document, finding)
        if clause is None:
            continue
        candidates.append(
            {
                "candidate_rule_id": f"CAND-{document.file_hash[:8].upper()}-{index:03d}",
                "document_name": document.document_name,
                "issue_type": finding.issue_type,
                "problem_title": finding.problem_title,
                "source_section": finding.source_section,
                "section_path": finding.section_path,
                "clause_id": finding.clause_id,
                "source_text": finding.source_text,
                "why_it_is_risky": finding.why_it_is_risky,
                "rewrite_suggestion": finding.rewrite_suggestion,
                "suggested_merge_key": _suggested_merge_key(finding),
                "trigger_keywords": _keyword_candidates(clause.text),
                "false_positive_risk": _false_positive_risk(finding),
                "generation_reason": f"LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。",
                "benchmark_hint": finding.issue_type,
            }
        )
    return candidates


def run_benchmark_gate(rule_candidates: list[dict[str, object]]) -> dict[str, object]:
    benchmark = benchmark_summary()
    covered = set(benchmark.get("issue_types_covered", []))
    results: list[dict[str, object]] = []
    pass_count = 0
    for item in rule_candidates:
        issue_type = str(item["issue_type"])
        status = "covered" if issue_type in covered else "needs_benchmark"
        if status == "covered":
            pass_count += 1
        results.append(
            {
                "candidate_rule_id": item["candidate_rule_id"],
                "issue_type": issue_type,
                "status": status,
                "reason": (
                    "当前 benchmark 已覆盖该问题类型，可进入规则候选复核。"
                    if status == "covered"
                    else "当前 benchmark 尚未覆盖该问题类型，建议先补样本后再转正式规则。"
                ),
            }
        )
    return {
        "candidate_count": len(rule_candidates),
        "covered_count": pass_count,
        "needs_benchmark_count": len(rule_candidates) - pass_count,
        "results": results,
        "status": "ok" if len(rule_candidates) == 0 or pass_count == len(rule_candidates) else "needs_attention",
    }


def write_improvement_outputs(
    output_stem: str,
    rule_candidates: list[dict[str, object]],
    benchmark_gate: dict[str, object],
) -> LLMReviewArtifacts:
    paths = detect_paths()
    paths.improvement_root.mkdir(parents=True, exist_ok=True)
    candidate_json_path = paths.improvement_root / f"{output_stem}-rule-candidates.json"
    candidate_md_path = paths.improvement_root / f"{output_stem}-rule-candidates.md"
    benchmark_json_path = paths.improvement_root / f"{output_stem}-benchmark-gate.json"
    benchmark_md_path = paths.improvement_root / f"{output_stem}-benchmark-gate.md"

    candidate_json_path.write_text(json.dumps(rule_candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    candidate_md_path.write_text(_render_rule_candidates(rule_candidates), encoding="utf-8")
    benchmark_json_path.write_text(json.dumps(benchmark_gate, ensure_ascii=False, indent=2), encoding="utf-8")
    benchmark_md_path.write_text(_render_benchmark_gate(benchmark_gate), encoding="utf-8")

    return LLMReviewArtifacts(
        added_findings=[],
        rule_candidates=[],
        benchmark_gate={},
        candidate_json_path=str(candidate_json_path),
        candidate_md_path=str(candidate_md_path),
        benchmark_json_path=str(benchmark_json_path),
        benchmark_md_path=str(benchmark_md_path),
    )


def _run_template_mismatch_task(
    document: NormalizedDocument,
    review: ReviewResult,
    client: OpenAICompatibleLLMClient,
) -> list[Finding]:
    candidate_clauses = [
        clause
        for clause in document.clauses
        if any(
            token in clause.text
            for token in ("系统", "芯片", "平台", "软件", "保洁", "清运", "以采购人的实际需求为准", "垃圾")
        )
    ]
    if not candidate_clauses:
        return []
    prompt = _build_task_prompt(
        task_name="template_mismatch",
        instruction=(
            "判断这些条款是否与当前采购标的存在明显领域错位、模板错贴或开放式义务外扩。"
            "如果成立，返回 should_flag=true，并给出问题标题、风险说明、改写建议。"
        ),
        document=document,
        clauses=candidate_clauses,
        review=review,
    )
    payload = _safe_chat_json(client, prompt, default={"findings": []})
    return _findings_from_payload(
        document,
        payload,
        issue_type_default="other",
        allowed_clause_ids={clause.clause_id for clause in candidate_clauses},
    )


def _run_scoring_structure_task(
    document: NormalizedDocument,
    review: ReviewResult,
    client: OpenAICompatibleLLMClient,
) -> list[Finding]:
    candidate_clauses = [
        clause
        for clause in document.clauses
        if clause.section_path and "评标信息" in clause.section_path and any(token in clause.text for token in ("评分", "样品", "认证", "业绩", "方案", "得"))
    ]
    if not candidate_clauses:
        return []
    prompt = _build_task_prompt(
        task_name="scoring_structure",
        instruction=(
            "判断评分结构中是否存在样品评分主观性过强、认证评分结构失衡、资格或企业属性混入评分等问题。"
            "仅返回当前 review 尚未稳定表达出来的新增问题。"
        ),
        document=document,
        clauses=candidate_clauses[:20],
        review=review,
    )
    payload = _safe_chat_json(client, prompt, default={"findings": []})
    return _findings_from_payload(
        document,
        payload,
        issue_type_default="scoring_structure_imbalance",
        allowed_clause_ids={clause.clause_id for clause in candidate_clauses},
    )


def _run_commercial_chain_task(
    document: NormalizedDocument,
    review: ReviewResult,
    client: OpenAICompatibleLLMClient,
) -> list[Finding]:
    candidate_clauses = [
        clause
        for clause in document.clauses
        if any(token in clause.text for token in ("验收", "付款", "抽样", "检测", "违约", "责任", "负全责", "实际需求为准"))
    ]
    if not candidate_clauses:
        return []
    prompt = _build_task_prompt(
        task_name="commercial_chain",
        instruction=(
            "把交货、验收、抽检、付款、违约和责任条款联合起来判断。"
            "只输出组合后才看得出的商务链路风险，不要重复已有单句结论。"
        ),
        document=document,
        clauses=candidate_clauses[:20],
        review=review,
    )
    payload = _safe_chat_json(client, prompt, default={"findings": []})
    return _findings_from_payload(
        document,
        payload,
        issue_type_default="one_sided_commercial_term",
        allowed_clause_ids={clause.clause_id for clause in candidate_clauses},
    )


def _build_task_prompt(
    *,
    task_name: str,
    instruction: str,
    document: NormalizedDocument,
    clauses: list[Clause],
    review: ReviewResult,
) -> str:
    lines = [
        f"任务: {task_name}",
        f"文件: {document.document_name}",
        f"采购标的摘要: {_document_domain_summary(document)}",
        "已存在 findings 摘要:",
    ]
    for finding in review.findings[:15]:
        lines.append(f"- {finding.finding_id}: {finding.problem_title} | {finding.issue_type} | {finding.source_text[:80]}")
    lines.extend(
        [
            "候选条款:",
            *[
                f"- clause_id={clause.clause_id} | section={clause.section_path} | lines={clause.line_start}-{clause.line_end} | text={clause.text}"
                for clause in clauses
            ],
            "输出 JSON 对象，格式如下：",
            '{',
            '  "findings": [',
            '    {',
            '      "should_flag": true,',
            '      "clause_id": "条款编号",',
            '      "issue_type": "问题类型",',
            '      "problem_title": "问题标题",',
            '      "why_it_is_risky": "风险说明",',
            '      "rewrite_suggestion": "改写建议"',
            "    }",
            "  ]",
            "}",
            f"要求: {instruction}",
        ]
    )
    return "\n".join(lines)


def _safe_chat_json(
    client: OpenAICompatibleLLMClient,
    prompt: str,
    *,
    default: dict[str, object],
) -> dict[str, object]:
    try:
        content = client.chat(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=prompt),
            ]
        )
        return json.loads(_extract_json_object(content))
    except Exception:
        return default


def _extract_json_object(content: str) -> str:
    text = content.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    raise ValueError("LLM response does not contain a JSON object")


def _findings_from_payload(
    document: NormalizedDocument,
    payload: dict[str, object],
    *,
    issue_type_default: str,
    allowed_clause_ids: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    for index, item in enumerate(payload.get("findings", []), start=1):
        if not isinstance(item, dict) or not item.get("should_flag"):
            continue
        clause_id = str(item.get("clause_id", ""))
        if clause_id not in allowed_clause_ids:
            continue
        clause = _find_clause_by_id(document, clause_id)
        if clause is None:
            continue
        findings.append(
            Finding(
                finding_id=f"LLM-{index:03d}",
                document_name=document.document_name,
                problem_title=str(item.get("problem_title") or "大模型识别到新增风险"),
                page_hint=clause.page_hint,
                clause_id=clause.clause_id,
                source_section=clause.source_section or clause.section_path or "",
                section_path=clause.section_path,
                table_or_item_label=clause.table_or_item_label,
                text_line_start=clause.line_start,
                text_line_end=clause.line_end,
                source_text=_representative_excerpt(clause.text),
                issue_type=str(item.get("issue_type") or issue_type_default),
                risk_level="medium",
                severity_score=2,
                confidence="medium",
                compliance_judgment="potentially_problematic",
                why_it_is_risky=str(item.get("why_it_is_risky") or "大模型识别到该条款存在边界风险。"),
                impact_on_competition_or_performance="可能影响公平竞争、履约边界或合同可执行性。",
                legal_or_policy_basis=None,
                rewrite_suggestion=str(item.get("rewrite_suggestion") or "建议结合项目场景进一步细化条款。"),
                needs_human_review=True,
                human_review_reason="该问题由本地大模型在边界判断任务中新增，建议复核后决定是否入正式规则库。",
                finding_origin="llm_added",
            )
        )
    return findings


def _merge_added_findings(review: ReviewResult, added_findings: list[Finding]) -> ReviewResult:
    if not added_findings:
        return review
    result = deepcopy(review)
    existing_keys = {
        (finding.issue_type, finding.clause_id, finding.problem_title)
        for finding in result.findings
    }
    for finding in added_findings:
        key = (finding.issue_type, finding.clause_id, finding.problem_title)
        if key not in existing_keys:
            result.findings.append(finding)
            existing_keys.add(key)
    result.findings.sort(key=lambda item: (item.text_line_start, item.issue_type, item.problem_title))
    for index, finding in enumerate(result.findings, start=1):
        finding.finding_id = f"F-{index:03d}"
    risk_counts = {"high": 0, "medium": 0}
    for finding in result.findings:
        if finding.risk_level in risk_counts:
            risk_counts[finding.risk_level] += 1
    result.overall_risk_summary = (
        f"本地离线审查共形成 {len(result.findings)} 条去重 findings，其中高风险 {risk_counts['high']} 条、"
        f"中风险 {risk_counts['medium']} 条。当前结果已接入本地规则映射、引用资料检索和本地大模型边界判断，可作为正式审查前的离线初筛与复审输入。"
    )
    for finding in added_findings:
        if finding.problem_title not in result.items_for_human_review:
            result.items_for_human_review.append(finding.problem_title)
    return result


def _render_rule_candidates(rule_candidates: list[dict[str, object]]) -> str:
    lines = ["# 规则候选", ""]
    if not rule_candidates:
        lines.append("- 当前未生成新的规则候选。")
        return "\n".join(lines)
    for item in rule_candidates:
        lines.extend(
            [
                f"## {item['candidate_rule_id']} {item['problem_title']}",
                f"- issue_type: `{item['issue_type']}`",
                f"- source_section: `{item['section_path']}`",
                f"- source_text: `{item['source_text']}`",
                f"- trigger_keywords: `{', '.join(item['trigger_keywords'])}`",
                f"- false_positive_risk: `{item['false_positive_risk']}`",
                f"- generation_reason: {item['generation_reason']}",
                "",
            ]
        )
    return "\n".join(lines)


def _render_benchmark_gate(benchmark_gate: dict[str, object]) -> str:
    lines = ["# Benchmark Gate", ""]
    lines.append(f"- status: `{benchmark_gate.get('status')}`")
    lines.append(f"- candidate_count: `{benchmark_gate.get('candidate_count', 0)}`")
    lines.append(f"- covered_count: `{benchmark_gate.get('covered_count', 0)}`")
    lines.append(f"- needs_benchmark_count: `{benchmark_gate.get('needs_benchmark_count', 0)}`")
    lines.append("")
    for item in benchmark_gate.get("results", []):
        lines.append(
            f"- {item['candidate_rule_id']} | `{item['issue_type']}` | `{item['status']}` | {item['reason']}"
        )
    return "\n".join(lines)


def _document_domain_summary(document: NormalizedDocument) -> str:
    text = " ".join(clause.text for clause in document.clauses[:120])
    if any(token in text for token in ("医生服", "护士服", "病员服", "床品", "被套", "枕套", "洗手衣")):
        return "当前文件主标的更接近医用服装、病员服、床品等纺织类货物。"
    if any(token in text for token in ("内窥镜", "探头", "医用设备", "主机")):
        return "当前文件主标的更接近医疗设备类货物。"
    return "当前文件主标的需要结合候选条款进一步判断。"


def _find_clause_by_id(document: NormalizedDocument, clause_id: str) -> Clause | None:
    for clause in document.clauses:
        if clause.clause_id == clause_id:
            return clause
    return None


def _clause_for_finding(document: NormalizedDocument, finding: Finding) -> Clause | None:
    for clause in document.clauses:
        if clause.clause_id == finding.clause_id and clause.line_start == finding.text_line_start:
            return clause
    return _find_clause_by_id(document, finding.clause_id)


def _representative_excerpt(text: str, *, limit: int = 88) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _suggested_merge_key(finding: Finding) -> str:
    return f"llm-{finding.issue_type}"


def _keyword_candidates(text: str) -> list[str]:
    tokens = []
    for token in ("芯片", "系统", "保洁", "清运", "实际需求为准", "样品", "认证", "同一份报告", "负全责", "最终验收结果"):
        if token in text and token not in tokens:
            tokens.append(token)
    if tokens:
        return tokens
    compact = " ".join(text.split())
    return [compact[:16]] if compact else []


def _false_positive_risk(finding: Finding) -> str:
    if finding.issue_type in {"technical_justification_needed", "unclear_acceptance_standard"}:
        return "medium"
    if finding.issue_type in {"other", "scoring_structure_imbalance"}:
        return "low"
    return "medium"
