from __future__ import annotations

from collections import OrderedDict

from agent_compliance.knowledge.procurement_catalog import (
    CatalogClassification,
    classification_has_catalog_prefix,
    classification_has_domain,
)
from agent_compliance.pipelines.effective_requirement_scope_filter import (
    REQUIREMENT_SCOPE_BODY,
    classify_requirement_scope,
)
from agent_compliance.pipelines.review_arbiter import line_ranges_overlap
from agent_compliance.schemas import Finding


def shorten_section_path(section_path: str | None) -> str | None:
    if not section_path:
        return None
    parts = [part.strip() for part in section_path.split("-") if part.strip()]
    shortened = [shorten_segment(part) for part in parts]
    return "-".join(shortened)


def shorten_segment(segment: str) -> str:
    if len(segment) <= 36:
        return segment
    return f"{segment[:30]}..."


def normalized_source_signature(source_text: str) -> str:
    normalized = "".join(ch for ch in source_text if ch.isalnum())
    return normalized[:80]


def is_appendix_duplicate_candidate(finding: Finding) -> bool:
    if not finding.section_path:
        return False
    normalized = "".join(finding.section_path.split())
    return "第四章" in normalized and "投标文件组成要求及格式" in normalized


def matches_existing_signature(candidate: tuple[str, str], primary_signatures: list[tuple[str, str]]) -> bool:
    candidate_issue, candidate_text = candidate
    for issue_type, primary_text in primary_signatures:
        if issue_type != candidate_issue:
            continue
        if candidate_text == primary_text:
            return True
        if candidate_text and primary_text and (candidate_text in primary_text or primary_text in candidate_text):
            return True
    return False


def drop_appendix_semantic_duplicates(findings: list[Finding]) -> list[Finding]:
    primary = [finding for finding in findings if not is_appendix_duplicate_candidate(finding)]
    appendix = [finding for finding in findings if is_appendix_duplicate_candidate(finding)]
    filtered = list(primary)
    for finding in appendix:
        if any(is_semantic_duplicate_of_primary(finding, existing) for existing in primary):
            continue
        filtered.append(finding)
    filtered.sort(key=lambda item: (item.text_line_start, item.issue_type, item.section_path or ""))
    return filtered


def is_semantic_duplicate_of_primary(candidate: Finding, primary: Finding) -> bool:
    if candidate.issue_type != primary.issue_type:
        return False
    if candidate.clause_id and primary.clause_id and candidate.clause_id == primary.clause_id:
        return True
    if candidate.problem_title == primary.problem_title and signatures_overlap(candidate.source_text, primary.source_text):
        return True
    if signatures_overlap(candidate.source_text, primary.source_text) and line_ranges_overlap(candidate, primary, tolerance=3):
        return True
    return False


def signatures_overlap(left: str, right: str) -> bool:
    left_sig = normalized_source_signature(left)
    right_sig = normalized_source_signature(right)
    if not left_sig or not right_sig:
        return False
    return left_sig == right_sig or left_sig in right_sig or right_sig in left_sig


def build_theme_excerpt(source_text: str | None) -> str:
    if not source_text:
        return ""
    parts = [part.strip() for part in source_text.split("；") if part.strip()]
    unique_parts = list(OrderedDict.fromkeys(parts))
    if len(unique_parts) <= 2:
        return "；".join(unique_parts)
    return "；".join(unique_parts[:2]) + f" 等{len(unique_parts)}项"


def select_representative_evidence(
    finding: Finding,
    classification: CatalogClassification | None = None,
) -> str:
    source_text = finding.source_text or ""
    if not source_text:
        return ""
    parts = [part.strip() for part in source_text.split("；") if part.strip()]
    if len(parts) <= 1:
        return clip_excerpt(source_text, limit=78)
    effective_parts = [
        part
        for part in parts
        if classify_requirement_scope(
            clause_id=finding.clause_id,
            section_path=finding.section_path,
            source_section=finding.source_section,
            table_or_item_label=finding.table_or_item_label,
            text=part,
        ).category
        == REQUIREMENT_SCOPE_BODY
    ]
    if effective_parts:
        parts = effective_parts

    title = finding.problem_title
    keywords = evidence_keywords_for_title(title, classification=classification)
    ranked = sorted(
        OrderedDict.fromkeys(parts),
        key=lambda part: (
            -sum(1 for keyword in keywords if keyword in part),
            len(part),
        ),
    )
    selected = [clip_excerpt(part, limit=72) for part in ranked[:2]]
    excerpt = "；".join(selected)
    if len(ranked) > 2:
        excerpt = f"{excerpt} 等{len(ranked)}项"
    return excerpt


def evidence_keywords_for_title(
    title: str,
    *,
    classification: CatalogClassification | None = None,
) -> tuple[str, ...]:
    mapping = {
        "评分项名称、内容和评分证据之间不一致": (
            "工程案例",
            "检测报告",
            "CMA",
            "资产总额",
            "营业收入",
            "净利润",
            "标准委员会",
            "科技型中小企业",
            "ISO20000",
        ),
        "人员与团队评分混入错位证书并过度堆叠条件": (
            "学位",
            "博士",
            "硕士",
            "职称证书",
            "高级工程师",
            "奖项",
            "项目经验",
            "特种设备",
            "高级餐饮业职业经理人",
            "食品安全管理员",
            "中式烹调师",
            "面点师",
        ),
        "现场演示分值过高且签到要求形成额外门槛": (
            "可运行展示系统",
            "系统原型",
            "PPT",
            "视频",
            "60分钟",
            "签到",
            "得 0 分",
        ),
        "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担": (
            "付款",
            "验收",
            "送检",
            "检测",
            "第三方质量检测",
            "专家评审",
            "24小时",
            "到场",
            "解除合同",
            "售后服务保证金",
            "满意度评价",
            "服务费挂钩",
            "按1%扣减",
            "按2%扣减",
            "按3%扣减",
        ),
    }
    keywords = list(mapping.get(title, ()))
    if classification_has_catalog_prefix(classification, "C160") or classification_has_domain(classification, "information_system"):
        keywords.extend(("软件", "平台", "接口", "软件著作权", "演示", "签到"))
    if any(
        classification_has_catalog_prefix(classification, prefix) for prefix in ("C2307", "C2309", "C2315")
    ) or classification_has_domain(classification, "signage_printing_service"):
        keywords.extend(("宣传", "印刷", "导视", "广告", "喷绘", "写真", "雕刻", "软件著作权"))
    if classification_has_catalog_prefix(classification, "A0232") or classification_has_domain(
        classification, "medical_device_goods"
    ):
        keywords.extend(("医疗设备", "检验报告", "CMA", "开机率", "验收", "送检"))
    if classification_has_catalog_prefix(classification, "C210400") or classification_has_domain(
        classification, "property_service"
    ):
        keywords.extend(("医院物业", "履约评价", "服务费挂钩", "满意度", "到场", "驻场"))
    return tuple(OrderedDict.fromkeys(keywords))


def representative_excerpt(source_text: str) -> str:
    parts = [part.strip() for part in source_text.split("；") if part.strip()]
    if not parts:
        return source_text
    normalized_parts = list(OrderedDict.fromkeys(parts))
    snippets = [clip_excerpt(part) for part in normalized_parts[:2]]
    excerpt = "；".join(snippets)
    if len(normalized_parts) > 2:
        excerpt = f"{excerpt} 等{len(normalized_parts)}项"
    return excerpt


def merge_optional_text(values, separator: str = "；") -> str | None:
    merged = [value for value in OrderedDict.fromkeys(value for value in values if value)]
    if not merged:
        return None
    return separator.join(merged)


def clip_excerpt(text: str, *, limit: int = 60) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
