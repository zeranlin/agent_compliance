from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from agent_compliance.config import LLMConfig, detect_paths
from agent_compliance.evals.runner import benchmark_summary
from agent_compliance.knowledge.legal_authority_reasoner import apply_legal_authority_reasoner
from agent_compliance.knowledge.procurement_catalog import (
    CatalogClassification,
    classify_procurement_catalog,
)
from agent_compliance.models.llm_client import ChatMessage, OpenAICompatibleLLMClient
from agent_compliance.pipelines.confidence_calibrator import apply_confidence_calibrator
from agent_compliance.schemas import Clause, Finding, NormalizedDocument, ReviewResult
from agent_compliance.pipelines.review import reconcile_review_result


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
    difference_learning: dict[str, object] | None = None
    candidate_json_path: str | None = None
    candidate_md_path: str | None = None
    benchmark_json_path: str | None = None
    benchmark_md_path: str | None = None
    difference_json_path: str | None = None
    difference_md_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "added_findings": [finding.to_dict() for finding in self.added_findings],
            "rule_candidates": self.rule_candidates,
            "benchmark_gate": self.benchmark_gate,
            "difference_learning": self.difference_learning,
            "candidate_json_path": self.candidate_json_path,
            "candidate_md_path": self.candidate_md_path,
            "benchmark_json_path": self.benchmark_json_path,
            "benchmark_md_path": self.benchmark_md_path,
            "difference_json_path": self.difference_json_path,
            "difference_md_path": self.difference_md_path,
        }


def apply_llm_review_tasks(
    document: NormalizedDocument,
    review: ReviewResult,
    llm_config: LLMConfig,
    *,
    output_stem: str,
) -> tuple[ReviewResult, LLMReviewArtifacts]:
    empty = LLMReviewArtifacts(
        added_findings=[],
        rule_candidates=[],
        benchmark_gate={"status": "llm_disabled"},
        difference_learning={"status": "llm_disabled"},
    )
    if not llm_config.enabled:
        return review, empty

    client = OpenAICompatibleLLMClient(llm_config)
    classification = classify_procurement_catalog(document)
    added_findings: list[Finding] = []
    added_findings.extend(_run_document_audit_task(document, review, client, classification=classification))
    added_findings.extend(_run_template_mismatch_task(document, review, client))
    added_findings.extend(_run_scoring_structure_task(document, review, client))
    added_findings.extend(_run_commercial_chain_task(document, review, client))
    added_findings = apply_legal_authority_reasoner(added_findings)
    added_findings = apply_confidence_calibrator(added_findings)

    merged_review = _merge_added_findings(review, added_findings)
    rule_candidates = generate_rule_candidates(document, merged_review, added_findings, classification=classification)
    benchmark_gate = run_benchmark_gate(rule_candidates)
    difference_learning = build_difference_learning_loop(
        document,
        merged_review,
        added_findings,
        rule_candidates,
        benchmark_gate,
        classification=classification,
    )
    artifacts = write_improvement_outputs(output_stem, rule_candidates, benchmark_gate, difference_learning)
    artifacts.added_findings = added_findings
    artifacts.rule_candidates = rule_candidates
    artifacts.benchmark_gate = benchmark_gate
    artifacts.difference_learning = difference_learning
    return merged_review, artifacts


def generate_rule_candidates(
    document: NormalizedDocument,
    review: ReviewResult,
    added_findings: list[Finding],
    *,
    classification: CatalogClassification | None = None,
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
                "primary_authority": finding.primary_authority,
                "secondary_authorities": finding.secondary_authorities or [],
                "legal_or_policy_basis": finding.legal_or_policy_basis,
                "applicability_logic": finding.applicability_logic,
                "confidence": finding.confidence,
                "needs_human_review": finding.needs_human_review,
                "human_review_reason": finding.human_review_reason,
                "primary_catalog_name": classification.primary_catalog_name if classification else None,
                "primary_domain_key": classification.primary_domain_key if classification else None,
                "primary_mapped_catalog_codes": classification.primary_mapped_catalog_codes if classification else [],
                "secondary_catalog_names": classification.secondary_catalog_names if classification else [],
                "secondary_mapped_catalog_codes": classification.secondary_mapped_catalog_codes if classification else [],
                "is_mixed_scope": classification.is_mixed_scope if classification else False,
            }
        )
    return candidates


def run_benchmark_gate(rule_candidates: list[dict[str, object]]) -> dict[str, object]:
    benchmark = benchmark_summary()
    covered = set(benchmark.get("issue_types_covered", []))
    results: list[dict[str, object]] = []
    pass_count = 0
    scene_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    authority_counts: dict[str, int] = {}
    for item in rule_candidates:
        issue_type = str(item["issue_type"])
        status = "covered" if issue_type in covered else "needs_benchmark"
        if status == "covered":
            pass_count += 1
        primary_catalog_name = str(item.get("primary_catalog_name") or "")
        primary_domain_key = str(item.get("primary_domain_key") or "")
        if primary_catalog_name:
            scene_counts[primary_catalog_name] = scene_counts.get(primary_catalog_name, 0) + 1
        if primary_domain_key:
            domain_counts[primary_domain_key] = domain_counts.get(primary_domain_key, 0) + 1
        primary_authority = str(item.get("primary_authority") or "")
        if primary_authority:
            authority_counts[primary_authority] = authority_counts.get(primary_authority, 0) + 1
        results.append(
            {
                "candidate_rule_id": item["candidate_rule_id"],
                "issue_type": issue_type,
                "status": status,
                "primary_authority": primary_authority or None,
                "primary_catalog_name": primary_catalog_name or None,
                "primary_domain_key": primary_domain_key or None,
                "is_mixed_scope": bool(item.get("is_mixed_scope", False)),
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
        "catalog_scene_summary": [
            {"primary_catalog_name": name, "candidate_count": count}
            for name, count in sorted(scene_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "domain_summary": [
            {"primary_domain_key": key, "candidate_count": count}
            for key, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "authority_summary": [
            {"primary_authority": key, "candidate_count": count}
            for key, count in sorted(authority_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "results": results,
        "status": "ok" if len(rule_candidates) == 0 or pass_count == len(rule_candidates) else "needs_attention",
    }


def write_improvement_outputs(
    output_stem: str,
    rule_candidates: list[dict[str, object]],
    benchmark_gate: dict[str, object],
    difference_learning: dict[str, object],
) -> LLMReviewArtifacts:
    paths = detect_paths()
    paths.improvement_root.mkdir(parents=True, exist_ok=True)
    candidate_json_path = paths.improvement_root / f"{output_stem}-rule-candidates.json"
    candidate_md_path = paths.improvement_root / f"{output_stem}-rule-candidates.md"
    benchmark_json_path = paths.improvement_root / f"{output_stem}-benchmark-gate.json"
    benchmark_md_path = paths.improvement_root / f"{output_stem}-benchmark-gate.md"
    difference_json_path = paths.improvement_root / f"{output_stem}-difference-learning.json"
    difference_md_path = paths.improvement_root / f"{output_stem}-difference-learning.md"

    candidate_json_path.write_text(json.dumps(rule_candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    candidate_md_path.write_text(_render_rule_candidates(rule_candidates), encoding="utf-8")
    benchmark_json_path.write_text(json.dumps(benchmark_gate, ensure_ascii=False, indent=2), encoding="utf-8")
    benchmark_md_path.write_text(_render_benchmark_gate(benchmark_gate), encoding="utf-8")
    difference_json_path.write_text(json.dumps(difference_learning, ensure_ascii=False, indent=2), encoding="utf-8")
    difference_md_path.write_text(_render_difference_learning(difference_learning), encoding="utf-8")

    return LLMReviewArtifacts(
        added_findings=[],
        rule_candidates=[],
        benchmark_gate={},
        difference_learning={},
        candidate_json_path=str(candidate_json_path),
        candidate_md_path=str(candidate_md_path),
        benchmark_json_path=str(benchmark_json_path),
        benchmark_md_path=str(benchmark_md_path),
        difference_json_path=str(difference_json_path),
        difference_md_path=str(difference_md_path),
    )


def build_difference_learning_loop(
    document: NormalizedDocument,
    review: ReviewResult,
    added_findings: list[Finding],
    rule_candidates: list[dict[str, object]],
    benchmark_gate: dict[str, object],
    *,
    classification: CatalogClassification | None = None,
) -> dict[str, object]:
    issue_types = sorted({finding.issue_type for finding in added_findings})
    rule_suggestions: list[dict[str, object]] = []
    analyzer_suggestions: list[dict[str, object]] = []
    prompt_suggestions: list[dict[str, object]] = []
    benchmark_suggestions: list[dict[str, object]] = []

    if "scoring_content_mismatch" in issue_types:
        rule_suggestions.append(
            {
                "target": "rules/scoring_rules.py",
                "suggestion": "补充评分项名称、评分内容、评分证据不一致的触发模式，优先识别方案项混入案例、商务项混入财务指标、认证项混入跨领域证书。",
            }
        )
        analyzer_suggestions.append(
            {
                "target": "scoring_semantic_consistency_engine",
                "suggestion": "继续把评分主题不一致的问题收束成更少的章节级主问题，并保留最具代表性的错位证据。",
            }
        )
        prompt_suggestions.append(
            {
                "target": "llm_review.scoring_structure",
                "suggestion": "要求模型优先判断评分项名称、评分证据和计分目的是否一致，并结合当前主品目区分哪些证书、案例和证明材料属于错位内容。",
            }
        )
    if "template_mismatch" in issue_types or any("混合采购场景" in finding.problem_title for finding in added_findings):
        analyzer_suggestions.append(
            {
                "target": "mixed_scope_boundary_engine/domain_match_engine",
                "suggestion": "增强药品、设备、信息化接口等混合采购边界判断，区分合理配套设备要求与超出药品采购边界的附加义务。",
            }
        )
        prompt_suggestions.append(
            {
                "target": "llm_review.document_audit",
                "suggestion": "要求模型先结合主品目、官方品目映射和混合采购标记识别主标的，再判断自动化设备、系统接口和扩展服务是否超出当前采购边界。",
            }
        )
    if any(
        finding.issue_type in {"one_sided_commercial_term", "payment_acceptance_linkage", "unclear_acceptance_standard"}
        for finding in added_findings
    ):
        rule_suggestions.append(
            {
                "target": "rules/contract_rules.py",
                "suggestion": "补充履约保证金转售后保证金、长期资金占用、验收费转嫁和开放式需求边界等商务链路规则。",
            }
        )
        analyzer_suggestions.append(
            {
                "target": "commercial_lifecycle_analyzer",
                "suggestion": "从付款、验收、复检、售后和责任承担全链路识别整体偏重供应商承担的后果链，并结合当前品目场景区分货物安装、物业服务和医疗设备的不同履约模式。",
            }
        )
    uncovered = [item for item in benchmark_gate.get("results", []) if item.get("status") != "covered"]
    for item in uncovered[:5]:
        benchmark_suggestions.append(
            {
                "target": item.get("issue_type"),
                "suggestion": f"补充 {item.get('issue_type')} 类型 benchmark，用于验证新规则和主题分析器是否真的提升召回。",
            }
        )
    if not benchmark_suggestions and issue_types:
        for issue_type in issue_types[:4]:
            benchmark_suggestions.append(
                {
                    "target": issue_type,
                    "suggestion": f"为 {issue_type} 类型补充更贴近真实采购文件的差异样本和期望主问题。",
                }
            )

    evidence = [
        {
            "problem_title": finding.problem_title,
            "issue_type": finding.issue_type,
            "source_text": finding.source_text,
            "section_path": finding.section_path,
            "finding_origin": finding.finding_origin,
        }
        for finding in added_findings[:8]
    ]

    return {
        "status": "ok",
        "document_name": document.document_name,
        "file_hash": document.file_hash,
        "primary_catalog_name": classification.primary_catalog_name if classification else None,
        "primary_domain_key": classification.primary_domain_key if classification else None,
        "primary_mapped_catalog_codes": classification.primary_mapped_catalog_codes if classification else [],
        "secondary_catalog_names": classification.secondary_catalog_names if classification else [],
        "secondary_mapped_catalog_codes": classification.secondary_mapped_catalog_codes if classification else [],
        "is_mixed_scope": classification.is_mixed_scope if classification else False,
        "added_issue_types": issue_types,
        "added_finding_count": len(added_findings),
        "rule_candidate_count": len(rule_candidates),
        "review_theme_count": len([finding for finding in review.findings if finding.finding_origin == "analyzer"]),
        "suggestions": {
            "rules": rule_suggestions,
            "theme_analyzers": analyzer_suggestions,
            "llm_prompts": prompt_suggestions,
            "benchmark": benchmark_suggestions,
        },
        "evidence": evidence,
    }


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
        issue_type_default="template_mismatch",
        allowed_clause_ids={clause.clause_id for clause in candidate_clauses},
        allowed_issue_types={"template_mismatch"},
    )


def _run_document_audit_task(
    document: NormalizedDocument,
    review: ReviewResult,
    client: OpenAICompatibleLLMClient,
    *,
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    candidate_clauses = _document_audit_candidate_clauses(document)
    if not candidate_clauses:
        return []
    prompt = _build_task_prompt(
        task_name="document_audit",
        instruction=(
            "你正在做全文辅助扫描。请优先输出章节级主问题，而不是零散碎点。"
            "重点关注资格条件中的行业错位资质和一般财务门槛、评分项中的内容错位、"
            "技术要求中过窄的固定年份限制，以及付款、免责、复检费用等商务边界问题。"
            "不要重复已有 findings；如果多个候选条款属于同一章节主题，请尽量合成一条主问题。"
        ),
        document=document,
        clauses=candidate_clauses[:24],
        review=review,
        classification=classification,
    )
    payload = _safe_chat_json(client, prompt, default={"findings": []})
    findings = _findings_from_payload(
        document,
        payload,
        issue_type_default="qualification_domain_mismatch",
        allowed_clause_ids={clause.clause_id for clause in candidate_clauses},
        allowed_issue_types={
            "excessive_supplier_qualification",
            "qualification_domain_mismatch",
            "duplicative_scoring_advantage",
            "scoring_content_mismatch",
            "geographic_restriction",
            "technical_justification_needed",
            "one_sided_commercial_term",
            "unclear_acceptance_standard",
            "template_mismatch",
        },
    )
    findings.extend(_fallback_document_audit_findings(document, review, candidate_clauses, classification=classification))
    return _dedupe_added_findings(findings)


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

    findings: list[Finding] = []
    allowed_issue_types = {
            "ambiguous_requirement",
            "irrelevant_certification_or_award",
            "duplicative_scoring_advantage",
            "scoring_content_mismatch",
            "excessive_scoring_weight",
            "scoring_structure_imbalance",
            "post_award_proof_substitution",
            "geographic_restriction",
    }
    sample_clauses = [
        clause for clause in candidate_clauses if any(token in clause.text for token in ("样品", "评审为优", "得80%分", "得 80%分"))
    ]
    certification_clauses = [
        clause
        for clause in candidate_clauses
        if any(token in clause.text for token in ("环境标志产品认证", "管理体系认证", "认证证书", "成立时间不足三个月", "认证"))
    ]
    task_groups = [
        (
            "scoring_sample",
            sample_clauses,
            "重点判断样品评分是否主观性过强、分档跳跃过大、缺少量化锚点。",
            "ambiguous_requirement",
        ),
        (
            "scoring_certification",
            certification_clauses,
            "重点判断认证评分是否结构失衡、是否允许以成立时间不足三个月等理由替代真实取得证书。",
            "scoring_structure_imbalance",
        ),
    ]
    for task_name, clauses, instruction, issue_type_default in task_groups:
        if not clauses:
            continue
        prompt = _build_task_prompt(
            task_name=task_name,
            instruction=instruction,
            document=document,
            clauses=clauses[:12],
            review=review,
        )
        payload = _safe_chat_json(client, prompt, default={"findings": []})
        findings.extend(
            _findings_from_payload(
                document,
                payload,
                issue_type_default=issue_type_default,
                allowed_clause_ids={clause.clause_id for clause in clauses},
                allowed_issue_types=allowed_issue_types,
            )
        )

    findings.extend(_fallback_scoring_findings(document, review, sample_clauses, certification_clauses))
    return _dedupe_added_findings(findings)


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
    findings = _findings_from_payload(
        document,
        payload,
        issue_type_default="one_sided_commercial_term",
        allowed_clause_ids={clause.clause_id for clause in candidate_clauses},
        allowed_issue_types={"unclear_acceptance_standard", "one_sided_commercial_term", "payment_acceptance_linkage"},
    )
    findings.extend(_fallback_commercial_findings(document, review, candidate_clauses))
    return _dedupe_added_findings(findings)


def _build_task_prompt(
    *,
    task_name: str,
    instruction: str,
    document: NormalizedDocument,
    clauses: list[Clause],
    review: ReviewResult,
    classification: CatalogClassification | None = None,
) -> str:
    lines = [
        f"任务: {task_name}",
        f"文件: {document.document_name}",
        f"采购标的摘要: {_document_domain_summary(document, classification=classification)}",
        "已存在 findings 摘要:",
    ]
    for finding in review.findings[:15]:
        lines.append(f"- {finding.finding_id}: {finding.problem_title} | {finding.issue_type} | {finding.source_text[:80]}")
    lines.extend(
        [
            "候选条款:",
            *[
                f"- clause_ref={clause.line_start}:{clause.clause_id} | clause_id={clause.clause_id} | section={clause.section_path} | lines={clause.line_start}-{clause.line_end} | text={clause.text}"
                for clause in clauses
            ],
            "输出 JSON 对象，格式如下：",
            '{',
            '  "findings": [',
            '    {',
            '      "should_flag": true,',
            '      "clause_ref": "行号:条款编号",',
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
    allowed_issue_types: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    allowed_clause_refs = {f"{clause.line_start}:{clause.clause_id}" for clause in document.clauses if clause.clause_id in allowed_clause_ids}
    for index, item in enumerate(payload.get("findings", []), start=1):
        if not isinstance(item, dict) or not item.get("should_flag"):
            continue
        clause_ref = str(item.get("clause_ref", ""))
        clause_id = str(item.get("clause_id", ""))
        clause = None
        if clause_ref and clause_ref in allowed_clause_refs:
            clause = _find_clause_by_ref(document, clause_ref)
        if clause is None:
            if clause_id not in allowed_clause_ids:
                continue
            clause = _find_clause_by_id(document, clause_id)
        if clause is None:
            continue
        issue_type = str(item.get("issue_type") or issue_type_default)
        if issue_type not in allowed_issue_types:
            issue_type = issue_type_default
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
                issue_type=issue_type,
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
        (
            finding.issue_type,
            finding.text_line_start,
            _normalized_summary_signature(f"{finding.problem_title} {finding.source_text}"),
        )
        for finding in result.findings
    }
    for finding in added_findings:
        key = (
            finding.issue_type,
            finding.text_line_start,
            _normalized_summary_signature(f"{finding.problem_title} {finding.source_text}"),
        )
        if key not in existing_keys:
            result.findings.append(finding)
            existing_keys.add(key)
    result = reconcile_review_result(result)
    result.overall_risk_summary = result.overall_risk_summary.replace(
        "当前结果已接入本地规则映射和引用资料检索，可作为正式审查前的离线初筛与复审输入。",
        "当前结果已接入本地规则映射、引用资料检索和本地大模型边界判断，可作为正式审查前的离线初筛与复审输入。",
    )
    return result


def _fallback_scoring_findings(
    document: NormalizedDocument,
    review: ReviewResult,
    sample_clauses: list[Clause],
    certification_clauses: list[Clause],
) -> list[Finding]:
    findings: list[Finding] = []
    if sample_clauses and not _review_has_issue(review, {"ambiguous_requirement"}, {clause.clause_id for clause in sample_clauses}):
        clause = sample_clauses[0]
        findings.append(
            _make_added_finding(
                document,
                clause,
                issue_type="ambiguous_requirement",
                problem_title="样品评分主观性强且缺少量化锚点",
                why_it_is_risky="样品评分主要依赖“优、良、中、差”等主观分档，且分值跳跃较大，缺少尺寸偏差、外观缺陷、做工质量等可核验锚点。",
                rewrite_suggestion="建议把样品评分拆成外观质量、做工缺陷、尺寸偏差、面料符合性等客观指标分项量化。",
            )
        )
    if certification_clauses and not _review_has_issue(review, {"scoring_structure_imbalance", "excessive_scoring_weight"}, {clause.clause_id for clause in certification_clauses}):
        clause = certification_clauses[0]
        findings.append(
            _make_added_finding(
                document,
                clause,
                issue_type="scoring_structure_imbalance",
                problem_title="认证评分结构失衡且可比性不足",
                why_it_is_risky="认证类评分集中出现且分值较高，同时允许以成立时间不足三个月等说明替代实际取得证书，会削弱评分时点的真实性和可比性。",
                rewrite_suggestion="建议降低认证类评分权重，并明确评分仅以投标截止时已取得的有效证明为准。",
            )
        )
    return findings


def _fallback_commercial_findings(
    document: NormalizedDocument,
    review: ReviewResult,
    clauses: list[Clause],
) -> list[Finding]:
    findings: list[Finding] = []
    target_clause = None
    for clause in clauses:
        if "实际需求为准" in clause.text or "最终验收结果" in clause.text:
            target_clause = clause
            break
    if target_clause and not _review_has_issue(review, {"unclear_acceptance_standard"}, {target_clause.clause_id}):
        findings.append(
            _make_added_finding(
                document,
                target_clause,
                issue_type="unclear_acceptance_standard",
                problem_title="验收结果单方确定且需求边界开放",
                why_it_is_risky="条款将验收结果过度交由采购人单方确定，且用“以采购人实际需求为准”扩大需求边界，容易导致整改标准和履约责任不清。",
                rewrite_suggestion="建议明确验收程序、复验机制和需求边界，删除开放式“以采购人实际需求为准”表述。",
            )
        )
    return findings


def _fallback_document_audit_findings(
    document: NormalizedDocument,
    review: ReviewResult,
    clauses: list[Clause],
    classification: CatalogClassification | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    theme_groups = [
        (
            ("有害生物防制", "SPCA", "资质证书", "登记证书", "年均纳税额", "经营业绩证明", "单项合同金额不低于"),
            {"qualification_domain_mismatch", "excessive_supplier_qualification"},
            "资格章节存在与标的不匹配的资质要求或一般经营门槛",
            "资格章节同时出现与采购标的不匹配的资质登记要求，以及一般纳税额、经营业绩或合同金额门槛，容易把模板残留和一般经营状况直接前置为准入条件。",
            "建议将资格条件收束为法定资格和与履约直接相关的必要能力，不宜混入错位资质和一般经营门槛。",
            "qualification_domain_mismatch",
        ),
        (
            ("工程案例", "CMA", "有机产品认证", "水运机电工程专项监理", "特种设备", "认证范围", "园区保洁"),
            {"scoring_content_mismatch", "qualification_domain_mismatch", "template_mismatch"},
            "评分或资质条款中存在与标的域不匹配的证书、案例或模板内容",
            "评分或资质条款中出现与当前采购标的领域不匹配的案例、证书、认证范围或模板内容，容易把无关材料错误地转化为得分点或准入条件。",
            "建议删除与项目标的不匹配的案例、证书和认证范围，仅保留与评分主题和履约目标直接相关的内容。",
            "scoring_content_mismatch",
        ),
        (
            ("软件著作权", "系统端口", "无缝对接", "平台", "接口"),
            {"template_mismatch", "scoring_content_mismatch", "technical_justification_needed"},
            "混合采购场景叠加信息化接口和软件化义务，边界不清",
            "当前采购文件在主标的之外叠加了软件著作权、系统端口或平台接口等信息化义务。若未说明这些内容与主采购标的的直接履约关系，容易形成混合采购边界不清。",
            "建议先明确主采购标的和配套边界，将系统接口、平台接入和软件化义务与主标的分开表述；不属于本次采购范围的应删除或另行采购。",
            "template_mismatch",
        ),
        (
            ("生产日期必须是", "专业工程师", "5 年以上"),
            {"technical_justification_needed", "excessive_supplier_qualification"},
            "技术与安装章节存在过窄时点或人员来源限定",
            "技术与安装章节同时对生产日期、人员来源或经验年限作过窄限定，容易将合理履约要求进一步收紧成事实上的排他条件。",
            "建议改为全新未使用且满足交付要求、具备相应专业背景和安装调试经验的中性表述，不宜固定年份或限定人员必须来自制造商厂。",
            "technical_justification_needed",
        ),
        (
            ("采购人不承担任何责任", "正常运行三个月后", "复检费用", "最终验收结果", "实际需求为准"),
            {"one_sided_commercial_term", "unclear_acceptance_standard", "payment_acceptance_linkage"},
            "商务章节存在付款绑定、责任失衡或验收边界不清问题",
            "商务章节将试运行、付款、责任免责和复检费用等问题叠加在一起，容易造成验收标准、责任划分和回款条件整体失衡。",
            "建议预先固定验收、试运行、复检和付款节点，并按过错来源划分责任与费用承担，避免开放式义务扩张。",
            "one_sided_commercial_term",
        ),
    ]
    for tokens, issue_types, title, rationale, rewrite, issue_type in theme_groups:
        matched_clauses = [item for item in clauses if any(token in item.text for token in tokens)]
        if not matched_clauses:
            continue
        if (
            title == "混合采购场景叠加信息化接口和软件化义务，边界不清"
            and classification is not None
            and classification.primary_domain_key == "information_system"
        ):
            continue
        if _review_has_issue(review, issue_types, {clause.clause_id for clause in matched_clauses}):
            continue
        findings.append(
            _make_theme_added_finding(
                document,
                matched_clauses,
                issue_type=issue_type,
                problem_title=title,
                why_it_is_risky=rationale,
                rewrite_suggestion=rewrite,
            )
        )
    return findings


def _document_audit_candidate_clauses(document: NormalizedDocument) -> list[Clause]:
    markers = (
        "资质证书",
        "登记证书",
        "年均纳税额",
        "经营业绩证明",
        "单项合同金额不低于",
        "工程案例",
        "CMA",
        "有机产品认证",
        "水运机电工程专项监理",
        "特种设备",
        "生产日期必须是",
        "专业工程师",
        "采购人不承担任何责任",
        "正常运行三个月后",
        "复检费用",
        "最终验收结果",
        "实际需求为准",
    )
    return [clause for clause in document.clauses if any(token in clause.text for token in markers)]


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
                f"- primary_catalog_name: `{item.get('primary_catalog_name')}`",
                f"- primary_domain_key: `{item.get('primary_domain_key')}`",
                f"- primary_mapped_catalog_codes: `{', '.join(item.get('primary_mapped_catalog_codes', []))}`",
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
    scene_summary = benchmark_gate.get("catalog_scene_summary", [])
    if isinstance(scene_summary, list) and scene_summary:
        lines.append("## Catalog Scene Summary")
        lines.append("")
        for item in scene_summary:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('primary_catalog_name') or '未识别品目'}`: `{item.get('candidate_count', 0)}`"
            )
        lines.append("")
    domain_summary = benchmark_gate.get("domain_summary", [])
    if isinstance(domain_summary, list) and domain_summary:
        lines.append("## Domain Summary")
        lines.append("")
        for item in domain_summary:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('primary_domain_key') or 'unknown'}`: `{item.get('candidate_count', 0)}`"
            )
        lines.append("")
    authority_summary = benchmark_gate.get("authority_summary", [])
    if isinstance(authority_summary, list) and authority_summary:
        lines.append("## Authority Summary")
        lines.append("")
        for item in authority_summary:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{item.get('primary_authority') or '未生成法规主依据'}`: `{item.get('candidate_count', 0)}`"
            )
        lines.append("")
    for item in benchmark_gate.get("results", []):
        lines.append(
            f"- {item['candidate_rule_id']} | `{item['issue_type']}` | `{item['status']}` | "
            f"`{item.get('primary_catalog_name') or '未识别品目'}` | "
            f"`{item.get('primary_authority') or '未生成法规主依据'}` | {item['reason']}"
        )
    return "\n".join(lines)


def _render_difference_learning(difference_learning: dict[str, object]) -> str:
    lines = ["# Difference Learning Loop", ""]
    lines.append(f"- status: `{difference_learning.get('status')}`")
    lines.append(f"- document_name: `{difference_learning.get('document_name')}`")
    lines.append(f"- primary_catalog_name: `{difference_learning.get('primary_catalog_name')}`")
    lines.append(f"- primary_domain_key: `{difference_learning.get('primary_domain_key')}`")
    lines.append(f"- primary_mapped_catalog_codes: `{', '.join(difference_learning.get('primary_mapped_catalog_codes', []))}`")
    lines.append(f"- added_finding_count: `{difference_learning.get('added_finding_count', 0)}`")
    lines.append(f"- rule_candidate_count: `{difference_learning.get('rule_candidate_count', 0)}`")
    lines.append("")
    lines.append("## Suggestions")
    lines.append("")
    suggestions = difference_learning.get("suggestions", {})
    for section_label, items in (
        ("rules", suggestions.get("rules", [])),
        ("theme_analyzers", suggestions.get("theme_analyzers", [])),
        ("llm_prompts", suggestions.get("llm_prompts", [])),
        ("benchmark", suggestions.get("benchmark", [])),
    ):
        lines.append(f"### {section_label}")
        if not items:
            lines.append("- 当前无新增建议。")
        else:
            for item in items:
                lines.append(f"- `{item.get('target')}`: {item.get('suggestion')}")
        lines.append("")
    lines.append("## Evidence")
    evidence = difference_learning.get("evidence", [])
    if not evidence:
        lines.append("- 当前无新增证据。")
    else:
        for item in evidence:
            lines.append(
                f"- `{item.get('issue_type')}` | {item.get('problem_title')} | {item.get('source_text')}"
            )
    return "\n".join(lines)


def _document_domain_summary(
    document: NormalizedDocument,
    *,
    classification: CatalogClassification | None = None,
) -> str:
    if classification is not None and classification.primary_catalog_name:
        summary = [f"主品目更接近：{classification.primary_catalog_name}。"]
        if classification.primary_mapped_catalog_codes:
            summary.append(f"官方品目映射：{', '.join(classification.primary_mapped_catalog_codes[:3])}。")
        if classification.secondary_catalog_names:
            summary.append(f"次品目候选：{', '.join(classification.secondary_catalog_names[:3])}。")
        if classification.is_mixed_scope:
            summary.append("当前文件存在混合采购或跨品目边界特征。")
        return "".join(summary)
    text = " ".join(clause.text for clause in document.clauses[:120])
    if any(token in text for token in ("医生服", "护士服", "病员服", "床品", "被套", "枕套", "洗手衣")):
        return "当前文件主标的更接近医用服装、病员服、床品等纺织类货物。"
    if any(token in text for token in ("内窥镜", "探头", "医用设备", "主机")):
        return "当前文件主标的更接近医疗设备类货物。"
    if any(token in text for token in ("柴油发电机", "发电机组", "机电设备", "安装调试")):
        return "当前文件主标的更接近柴油发电机组供货及安装类项目。"
    return "当前文件主标的需要结合候选条款进一步判断。"


def _find_clause_by_id(document: NormalizedDocument, clause_id: str) -> Clause | None:
    for clause in document.clauses:
        if clause.clause_id == clause_id:
            return clause
    return None


def _find_clause_by_ref(document: NormalizedDocument, clause_ref: str) -> Clause | None:
    try:
        line_start_str, clause_id = clause_ref.split(":", 1)
        line_start = int(line_start_str)
    except Exception:
        return None
    for clause in document.clauses:
        if clause.line_start == line_start and clause.clause_id == clause_id:
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
    for token in (
        "芯片",
        "系统",
        "保洁",
        "清运",
        "实际需求为准",
        "样品",
        "认证",
        "同一份报告",
        "负全责",
        "最终验收结果",
        "有害生物防制",
        "SPCA",
        "年均纳税额",
        "生产日期必须是",
        "专业工程师",
    ):
        if token in text and token not in tokens:
            tokens.append(token)
    if tokens:
        return tokens
    compact = " ".join(text.split())
    return [compact[:16]] if compact else []


def _false_positive_risk(finding: Finding) -> str:
    if finding.issue_type in {"technical_justification_needed", "unclear_acceptance_standard"}:
        return "medium"
    if finding.issue_type in {"template_mismatch", "qualification_domain_mismatch", "scoring_content_mismatch", "scoring_structure_imbalance"}:
        return "low"
    return "medium"


def _review_has_issue(review: ReviewResult, issue_types: set[str], clause_ids: set[str]) -> bool:
    return any(finding.issue_type in issue_types and finding.clause_id in clause_ids for finding in review.findings)


def _make_added_finding(
    document: NormalizedDocument,
    clause: Clause,
    *,
    issue_type: str,
    problem_title: str,
    why_it_is_risky: str,
    rewrite_suggestion: str,
) -> Finding:
    return Finding(
        finding_id="LLM-000",
        document_name=document.document_name,
        problem_title=problem_title,
        page_hint=clause.page_hint,
        clause_id=clause.clause_id,
        source_section=clause.source_section or clause.section_path or "",
        section_path=clause.section_path,
        table_or_item_label=clause.table_or_item_label,
        text_line_start=clause.line_start,
        text_line_end=clause.line_end,
        source_text=_representative_excerpt(clause.text),
        issue_type=issue_type,
        risk_level="medium",
        severity_score=2,
        confidence="medium",
        compliance_judgment="potentially_problematic",
        why_it_is_risky=why_it_is_risky,
        impact_on_competition_or_performance="可能影响公平竞争、履约边界或合同可执行性。",
        legal_or_policy_basis=None,
        rewrite_suggestion=rewrite_suggestion,
        needs_human_review=True,
        human_review_reason="该问题由本地大模型或其兜底分析链路新增，建议复核后决定是否入正式规则库。",
        finding_origin="llm_added",
    )


def _make_theme_added_finding(
    document: NormalizedDocument,
    clauses: list[Clause],
    *,
    issue_type: str,
    problem_title: str,
    why_it_is_risky: str,
    rewrite_suggestion: str,
) -> Finding:
    ordered = sorted(clauses, key=lambda item: (item.line_start, item.line_end))
    first = ordered[0]
    source_text = "；".join(list(dict.fromkeys(_representative_excerpt(clause.text) for clause in ordered[:3])))
    return Finding(
        finding_id="LLM-000",
        document_name=document.document_name,
        problem_title=problem_title,
        page_hint=" / ".join([clause.page_hint for clause in ordered if clause.page_hint][:3]) or first.page_hint,
        clause_id=first.clause_id,
        source_section=first.source_section or first.section_path or "",
        section_path=" / ".join([clause.section_path for clause in ordered if clause.section_path][:3]) or first.section_path,
        table_or_item_label=first.table_or_item_label,
        text_line_start=min(clause.line_start for clause in ordered),
        text_line_end=max(clause.line_end for clause in ordered),
        source_text=source_text,
        issue_type=issue_type,
        risk_level="high" if issue_type in {"qualification_domain_mismatch", "scoring_content_mismatch", "one_sided_commercial_term"} else "medium",
        severity_score=3 if issue_type in {"qualification_domain_mismatch", "scoring_content_mismatch", "one_sided_commercial_term"} else 2,
        confidence="medium",
        compliance_judgment="potentially_problematic",
        why_it_is_risky=why_it_is_risky,
        impact_on_competition_or_performance="可能影响公平竞争、履约边界或合同可执行性。",
        legal_or_policy_basis=None,
        rewrite_suggestion=rewrite_suggestion,
        needs_human_review=True,
        human_review_reason="该问题由本地大模型或其全文辅助扫描兜底链路新增，建议复核后决定是否入正式规则库。",
        finding_origin="llm_added",
    )


def _dedupe_added_findings(findings: list[Finding]) -> list[Finding]:
    deduped: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()
    for finding in findings:
        key = (
            finding.issue_type,
            finding.text_line_start,
            _normalized_summary_signature(f"{finding.problem_title} {finding.source_text}"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _normalized_summary_signature(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum())[:96]
