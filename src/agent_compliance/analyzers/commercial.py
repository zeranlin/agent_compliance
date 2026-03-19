from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable

from agent_compliance.knowledge.catalog_knowledge_profile import catalog_commercial_lifecycle_markers_for_classification
from agent_compliance.knowledge.procurement_catalog import (
    CatalogClassification,
    classification_has_catalog_prefix,
    classification_has_domain,
)
from agent_compliance.schemas import Finding, NormalizedDocument


ClausePredicate = Callable[[Any], bool]
ThemeBuilder = Callable[..., Finding]


def apply_commercial_analyzers(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    findings = _add_payment_evaluation_chain_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
        catalog_classification=catalog_classification,
    )
    findings = _add_service_evaluation_penalty_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
        catalog_classification=catalog_classification,
    )
    findings = _add_commercial_lifecycle_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
        catalog_classification=catalog_classification,
    )
    findings = _add_commercial_financing_burden_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
        catalog_classification=catalog_classification,
    )
    findings = _add_delivery_deadline_anomaly_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        catalog_classification=catalog_classification,
    )
    findings = _add_commercial_acceptance_fee_shift_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
        catalog_classification=catalog_classification,
    )
    findings = _add_liability_imbalance_theme_finding(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
        catalog_classification=catalog_classification,
    )
    findings = _add_geographic_tendency_findings(
        document,
        findings,
        build_theme_finding=build_theme_finding,
    )
    findings = _add_acceptance_boundary_findings(
        document,
        findings,
        build_theme_finding=build_theme_finding,
        is_substantive_commercial_clause=is_substantive_commercial_clause,
    )
    findings = _add_liability_balance_findings(
        document,
        findings,
        build_theme_finding=build_theme_finding,
    )
    return findings


def _add_service_evaluation_penalty_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("考核扣罚、满意度评价与解除合同后果叠加偏重" in finding.problem_title for finding in findings):
        return findings
    is_property_service = classification_has_domain(catalog_classification, "property_service") or classification_has_catalog_prefix(
        catalog_classification, "C210400"
    )
    is_catering_service = classification_has_domain(catalog_classification, "catering_service") or classification_has_catalog_prefix(
        catalog_classification, "C220400"
    )
    if not (is_property_service or is_catering_service):
        return findings
    markers = (
        "每月服务费与考核结果挂钩",
        "管理费直接挂钩",
        "满意度评价结果与服务费挂钩",
        "满意度评价在",
        "扣除当月物业服务费",
        "按1%扣减",
        "按2%扣减",
        "按3%扣减",
        "每低1分",
        "月得分",
        "考核不合格",
        "连续两次被评级为“中”",
        "甲方有权解除合同",
        "无条件服从",
        "及时修正《标准》",
    )
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        and any(marker in clause.text for marker in markers)
    ]
    payment_or_deduction = [
        clause for clause in clauses if any(marker in clause.text for marker in ("服务费", "扣除当月物业服务费", "按1%扣减", "按2%扣减", "按3%扣减", "每低1分"))
    ]
    termination_or_open_standard = [
        clause for clause in clauses if any(marker in clause.text for marker in ("甲方有权解除合同", "无条件服从", "及时修正《标准》", "考核不合格", "连续两次被评级为“中”"))
    ]
    if len(clauses) < 3 or not payment_or_deduction or not termination_or_open_standard:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="考核扣罚、满意度评价与解除合同后果叠加偏重",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "服务类条款将满意度评价、月度考核、服务费扣减和解除合同后果连续串联。"
                "当考核标准可调整、扣罚后果直接影响服务费且低分还能触发解除合同时，供应商在履约过程中会承受明显偏重的单方管理后果。"
            ),
            impact_on_competition_or_performance="可能使服务费回款、整改压力和解除合同风险同时上升，进而抬高服务项目的不确定性和竞争门槛。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议分别明确服务考核、满意度评价、扣罚比例和解除合同条件，删除开放式标准调整和自动叠加后果设计，不宜让月度评分直接连续放大为扣费和解除合同依据。",
            needs_human_review=True,
            human_review_reason="需结合服务考核制度、付款机制和采购人管理边界判断当前扣罚与解除合同后果是否明显超过项目实际履约需要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_commercial_financing_burden_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("商务条款设置异常资金占用安排" in finding.problem_title for finding in findings):
        return findings
    is_goods_install = classification_has_domain(catalog_classification, "equipment_installation") or classification_has_catalog_prefix(
        catalog_classification, "B0608"
    )
    is_medical_goods = classification_has_domain(catalog_classification, "medical_device_goods") or classification_has_catalog_prefix(
        catalog_classification, "A0232"
    )
    is_property_service = classification_has_domain(catalog_classification, "property_service") or classification_has_catalog_prefix(
        catalog_classification, "C210400"
    )
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in (
                "预算金额的5%作为履约担保",
                "以现金形式缴纳采购预算的5%作为履约保证金",
                "诚信履约备用金",
                "自动转为",
                "售后服务保证金",
                "质保期结束（36个月）",
                "36个月",
            )
        )
    ]
    if is_goods_install or is_medical_goods:
        clauses.extend(
            clause
            for clause in document.clauses
            if is_substantive_commercial_clause(clause)
            and any(marker in clause.text for marker in ("质保金", "售后保证金", "质量保证金", "验收后转为"))
        )
    if is_property_service:
        clauses.extend(
            clause
            for clause in document.clauses
            if is_substantive_commercial_clause(clause)
            and any(marker in clause.text for marker in ("履约保证金", "备用金", "扣除服务费", "考核扣罚"))
        )
    if len(clauses) < 1:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="商务条款设置异常资金占用安排",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务条款通过现金形式履约保证金、验收后自动转售后保证金以及较长质保占压等方式叠加设置资金占用安排。"
                "这类资金占用设计会明显增加供应商的前期履约成本和现金流压力。"
            ),
            impact_on_competition_or_performance="可能显著抬高报价和资金占用成本，并压缩可参与竞争的供应商范围。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议分别校准履约担保比例和备用金安排，不宜通过叠加式资金占用条件整体提高供应商履约门槛。",
            needs_human_review=True,
            human_review_reason="需结合财政支付、履约担保和项目供货周期判断相关商务安排是否合理并符合采购内控要求。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_delivery_deadline_anomaly_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("交货期限设置异常或明显失真" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("1000      个日历日内交货", "1000 个日历日内交货", "1000个日历日内交货")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="交货期限设置异常或明显失真",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "商务条款设置了与通常电子仪器仪表供货节奏明显不匹配的超长交货期限。"
                "这类失真的交货安排容易掩盖真实供货周期要求，也会增加合同履行和验收节点的不确定性。"
            ),
            impact_on_competition_or_performance="可能导致项目排期、履约责任和验收节点失真，并增加后续履约争议风险。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；中华人民共和国民法典",
            rewrite_suggestion="建议结合采购清单、供货周期和安装调试安排重设合理交货期限，避免使用明显失真的超长交付时限。",
            needs_human_review=True,
            human_review_reason="需结合采购内容、安装调试周期和项目建设时序判断当前交货期限是否属于录入错误或异常设置。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_commercial_acceptance_fee_shift_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("验收送检、检测和专家评审费用整体转嫁给供应商" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in ("报验", "送检", "检测报告出具", "专家评审", "自行消化", "空气检测", "监理", "整改费用", "复验费用", "抽检费用")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="unclear_acceptance_standard",
            problem_title="验收送检、检测和专家评审费用整体转嫁给供应商",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "验收条款将报验、送检、检测报告出具和专家评审等费用整体要求由供应商自行消化。"
                "当费用承担边界不随原因、责任和触发条件区分时，容易造成验收成本和争议风险单向转嫁。"
            ),
            impact_on_competition_or_performance="可能抬高供应商综合报价，并增加验收环节的费用争议和履约不确定性。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议区分法定抽检、常规验收、复检和专家评审等费用承担边界，不宜笼统要求所有相关费用均由供应商承担。",
            needs_human_review=True,
            human_review_reason="需结合验收流程、送检触发条件和责任分担规则判断相关费用转嫁安排是否合理。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_liability_imbalance_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("商务责任和违约后果设置明显偏重" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in (
                "采购人不承担任何责任",
                "相关损失及责任均与采购人无关",
                "一切事故",
                "负全责",
                "违约金按合同总价",
                "扣除全部履约保证金",
                "从应付货款中直接扣除",
                "直接扣减合同价款",
            )
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="商务责任和违约后果设置明显偏重",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务条款通过采购人绝对免责、供应商兜底承担全部责任以及较重违约金和扣款后果，形成了明显偏重的责任配置。"
                "当责任承担和违约后果都集中压向供应商时，合同权利义务容易失衡。"
            ),
            impact_on_competition_or_performance="可能显著提高报价不确定性和合同争议风险，并抬高供应商整体履约风险成本。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议按过错、责任来源和实际损失划分责任，删除绝对免责、当然扣款和过重违约后果设计。",
            needs_human_review=True,
            human_review_reason="需结合合同责任分配、违约情形和损失承担规则判断相关后果设置是否与项目实际履约风险相匹配。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_payment_evaluation_chain_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("付款条件与履约评价结果深度绑定且评价标准开放" in finding.problem_title for finding in findings):
        return findings
    is_property_service = classification_has_domain(catalog_classification, "property_service") or classification_has_catalog_prefix(
        catalog_classification, "C210400"
    )
    is_catering_service = classification_has_domain(catalog_classification, "catering_service") or classification_has_catalog_prefix(
        catalog_classification, "C220400"
    )
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in (
                "结合履约评价结果支付",
                "支付对应阶段款",
                "对应阶段款不予支付",
                "评价标准",
                "评价指标",
                "分值",
                "项目负责人可根据项目要求自行设定",
                "连续两次被评级为“中”",
                "累计扣款金额达到合同金额的 30%",
                "甲方有权解除合同",
                "每月服务费与考核结果挂钩",
                "管理费直接挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "按1%扣减",
                "按2%扣减",
                "按3%扣减",
                "提前告知",
                "并非最终版本",
                "及时修正《标准》",
                "无条件服从",
            )
        )
    ]
    evaluation_clauses = [
        clause
        for clause in clauses
        if any(
            marker in clause.text
            for marker in (
                "履约评价",
                "评价标准",
                "评价指标",
                "项目负责人可根据项目要求自行设定",
                "每月服务费与考核结果挂钩",
                "管理费直接挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "提前告知",
                "并非最终版本",
                "及时修正《标准》",
                "无条件服从",
            )
        )
    ]
    if not evaluation_clauses and (is_property_service or is_catering_service):
        return findings
    if len(clauses) < 3 or not evaluation_clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="付款条件与履约评价结果深度绑定且评价标准开放",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "条款将阶段付款与履约评价结果直接绑定，同时允许“评价标准、评价指标和分值”在履约过程中由项目负责人根据项目要求自行设定。"
                "当付款比例、整改要求和解除合同条件都受单方评价结果控制时，供应商回款和履约边界会明显失稳。"
            ),
            impact_on_competition_or_performance="可能导致付款条件和履约责任边界过度依赖采购人单方评价，增加报价不确定性和合同争议风险。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议预先固定履约评价标准、付款节点、整改条件和解除合同条件，不宜将付款比例和解除后果交由履约过程中单方开放式设定。",
            needs_human_review=True,
            human_review_reason="需结合合同文本、财政支付流程和履约考核制度判断付款与评价绑定的范围、比例和标准是否合理。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_commercial_lifecycle_theme_finding(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
    catalog_classification: CatalogClassification | None = None,
) -> list[Finding]:
    if any("履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担" in finding.problem_title for finding in findings):
        return findings
    profile_markers = catalog_commercial_lifecycle_markers_for_classification(catalog_classification)
    is_property_service = classification_has_domain(catalog_classification, "property_service") or classification_has_catalog_prefix(
        catalog_classification, "C210400"
    )
    is_goods_install = classification_has_domain(catalog_classification, "equipment_installation") or classification_has_catalog_prefix(
        catalog_classification, "B0608"
    )
    is_medical_goods = classification_has_domain(catalog_classification, "medical_device_goods") or classification_has_catalog_prefix(
        catalog_classification, "A0232"
    )
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in (
                "付款",
                "支付",
                "扣除当月物业服务费",
                "每低1分",
                "月得分",
                "考核不合格",
                "每月服务费与考核结果挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "按1%扣减",
                "按2%扣减",
                "按3%扣减",
                "验收",
                "送检",
                "检测",
                "专家评审",
                "24小时",
                "2小时",
                "12小时",
                "到场",
                "解除合同",
                "实际需求为准",
                "按市场价",
                "市场价格",
                "用户组织有关技术人员",
                "医院审核后方可制作",
                "其他合同未明示的相关工作",
                "必须有能力进行更改",
                "合同总价为固定不变价格",
                "售后服务保证金",
                "复检",
                "最终验收结果",
                "损失",
                "承担",
                "开机率",
                "备用设备",
                "财政审批",
                "暂停支付",
                *profile_markers,
            )
        )
    ]
    if is_property_service:
        clauses.extend(
            clause
            for clause in document.clauses
            if is_substantive_commercial_clause(clause)
            and any(marker in clause.text for marker in ("管理费直接挂钩", "满意度评价结果与服务费挂钩", "按1%扣减", "按2%扣减", "按3%扣减"))
        )
    if is_goods_install or is_medical_goods:
        clauses.extend(
            clause
            for clause in document.clauses
            if is_substantive_commercial_clause(clause)
            and any(marker in clause.text for marker in ("备用设备", "开机率", "暂停支付", "第三方质量检测", "财政审批"))
        )
    focused_clauses = [
        clause
        for clause in clauses
        if any(
            marker in clause.text
            for marker in (
                "付款",
                "支付",
                "阶段款",
                "扣除当月物业服务费",
                "每低1分",
                "月得分",
                "考核不合格",
                "每月服务费与考核结果挂钩",
                "满意度评价结果与服务费挂钩",
                "满意度评价在",
                "按1%扣减",
                "按2%扣减",
                "按3%扣减",
                "履约评价",
                "评价标准",
                "评价指标",
                "违约金",
                "解除合同",
                "24小时",
                "2 小时",
                "12 小时",
                "1 小时",
                "48小时",
                "到场",
                "送检",
                "检测",
                "专家评审",
                "终验",
                "开机率",
                "备用设备",
                "财政审批",
                "暂停支付",
                "第三方质量检测",
                "一切损失",
                "按市场价",
                "市场价格",
                "用户组织有关技术人员",
                "医院审核后方可制作",
                "其他合同未明示的相关工作",
                "必须有能力进行更改",
                "固定不变价格",
                *profile_markers,
            )
        )
    ]
    focused_clauses = _prefer_dominant_commercial_section(focused_clauses)
    responsibility_clauses = [
        clause
        for clause in focused_clauses
        if any(
            marker in clause.text
            for marker in (
                "24小时",
                "1 小时",
                "48小时",
                "解除合同",
                "违约金",
                "到场",
                "开机率",
                "备用设备",
                "一切损失",
                "扣除当月物业服务费",
                "每低1分",
                "月得分",
                "考核不合格",
            )
        )
    ]
    acceptance_clauses = [clause for clause in focused_clauses if any(marker in clause.text for marker in ("验收", "送检", "检测", "监理", "复检", "终验", "专家评审"))]
    if classification_has_domain(catalog_classification, "property_service"):
        responsibility_clauses = [
            clause
            for clause in focused_clauses
            if any(
                marker in clause.text
                for marker in ("24小时", "2 小时", "到场", "备用设备", "扣除当月物业服务费", "月得分", "满意度评价")
            )
        ]
    if classification_has_domain(catalog_classification, "equipment_installation"):
        acceptance_clauses = [
            clause
            for clause in focused_clauses
            if any(marker in clause.text for marker in ("安装", "调试", "验收", "终验", "开机率", "备用设备", "送检"))
        ]
    profile_clauses = [clause for clause in focused_clauses if any(marker in clause.text for marker in profile_markers)]
    if len(focused_clauses) < 3 or not responsibility_clauses or not acceptance_clauses:
        return findings
    if profile_markers and len(profile_clauses) < 2 and len(focused_clauses) > 4:
        return findings
    lifecycle_hint = ""
    if is_property_service:
        lifecycle_hint = " 在物业服务场景下，付款考核、驻场响应和服务质量责任边界本应预先固定，不宜交由履约过程中单方放大。"
    elif is_goods_install or is_medical_goods:
        lifecycle_hint = " 在设备供货并安装或医疗设备场景下，付款、验收、备用设备、开机率和售后到场条件应围绕安装调试与试运行边界分别明确。"
    findings.append(
        build_theme_finding(
            document=document,
            clauses=focused_clauses,
            issue_type="one_sided_commercial_term",
            problem_title="履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务与验收条款将付款节点、验收判定、送检复检费用、售后到场时限以及附加管理义务串联在一起，形成对供应商整体偏重的履约后果链。"
                "当这些后果叠加出现时，供应商不仅承担较高的履约成本，也难以预判回款、整改、到场响应和附加义务边界。"
                f"{lifecycle_hint}"
            ),
            impact_on_competition_or_performance="可能提高报价不确定性和合同争议风险，并通过整体偏重的履约后果抬高投标门槛。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议将付款、验收、复检、售后到场和附加管理义务拆分为独立条款，分别明确触发条件、责任来源和费用边界，并按当前品目的安装、服务或验收核心流程单独设定，不宜通过开放式义务和叠加式后果整体压重供应商责任。",
            needs_human_review=True,
            human_review_reason="需结合财政支付节点、验收流程和售后服务模式判断全链路责任配置是否超过项目实际履约需要。",
            finding_origin="analyzer",
        )
    )
    return findings


def _prefer_dominant_commercial_section(clauses):
    if not clauses:
        return clauses
    counts: OrderedDict[str, int] = OrderedDict()
    for clause in clauses:
        key = _top_level_section_key(clause.section_path)
        counts[key] = counts.get(key, 0) + 1
    dominant_key, dominant_count = max(counts.items(), key=lambda item: item[1])
    if dominant_count < 3:
        return clauses
    preferred = [clause for clause in clauses if _top_level_section_key(clause.section_path) == dominant_key]
    return preferred or clauses


def _top_level_section_key(section_path: str | None) -> str:
    if not section_path:
        return ""
    return section_path.split("-")[0].strip()


def _add_geographic_tendency_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
) -> list[Finding]:
    if any("驻场、短时响应或服务场地要求形成事实上的属地倾斜" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in (
                "1小时",
                "1 小时",
                "60分钟",
                "60 分钟",
                "2小时",
                "2 小时",
                "4小时",
                "4 小时",
                "12小时内提供备件",
                "24小时内到场",
                "高新区内",
                "固定的售后服务场所",
                "驻场",
                "现场服务",
                "本地售后网点",
                "驻点服务站",
                "本地备件库",
            )
        )
        and (
            any(
                marker in clause.text
                for marker in (
                    "到场",
                    "响应",
                    "驻场",
                    "现场服务",
                    "售后服务场所",
                    "固定的售后服务场所",
                    "本地售后网点",
                    "驻点服务站",
                    "本地备件库",
                    "高新区内",
                )
            )
            or not any(marker in clause.text for marker in ("24小时营业", "24小时营业及就餐服务", "供餐服务", "就餐服务"))
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="geographic_restriction",
            problem_title="驻场、短时响应或服务场地要求形成事实上的属地倾斜",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "条款同时设置驻场、短时到场响应或固定服务场地等要求。"
                "当这类要求未与明确的运维必要性绑定时，容易对本地或既有驻点供应商形成事实上的倾斜。"
            ),
            impact_on_competition_or_performance="可能抬高非本地供应商的投标准备和履约成本，间接压缩竞争范围。",
            legal_or_policy_basis="中华人民共和国政府采购法实施条例；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议将服务保障要求改为可核验的响应机制、驻场触发条件和运维指标，不直接以短时到场或固定场地替代履约能力要求。",
            needs_human_review=True,
            human_review_reason="需结合故障等级、运维场景和响应时限必要性判断相关驻场或短时响应要求是否确有业务依据。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_acceptance_boundary_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
    is_substantive_commercial_clause: ClausePredicate,
) -> list[Finding]:
    if any("验收程序、复检与最终确认边界不清" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if is_substantive_commercial_clause(clause)
        if any(
            marker in clause.text
            for marker in ("验收报告", "最终验收结果", "复检", "技术验收", "商务验收", "开箱检验")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="unclear_acceptance_standard",
            problem_title="验收程序、复检与最终确认边界不清",
            risk_level="medium",
            severity_score=2,
            confidence="high",
            compliance_judgment="potentially_problematic",
            why_it_is_risky=(
                "验收、复检、技术验收和商务验收等程序同时出现，但未清晰区分最终确认标准、复检触发条件和责任边界。"
                "这类设置容易在履约后期形成验收口径不一致和责任争议。"
            ),
            impact_on_competition_or_performance="可能导致验收标准不稳定、成本难估算和后续履约争议升级。",
            legal_or_policy_basis="政府采购需求管理办法（财政部）；履约验收规范要点（中国政府采购网）",
            rewrite_suggestion="建议逐条明确开箱检验、技术验收、商务验收、复检和最终确认的触发条件、结论效力及费用承担边界。",
            needs_human_review=True,
            human_review_reason="需结合项目验收流程、检测安排和责任划分规则判断各验收环节边界是否明确。",
            finding_origin="analyzer",
        )
    )
    return findings


def _add_liability_balance_findings(
    document: NormalizedDocument,
    findings: list[Finding],
    *,
    build_theme_finding: ThemeBuilder,
) -> list[Finding]:
    if any("商务责任和违约后果设置明显偏重" in finding.problem_title for finding in findings):
        return findings
    clauses = [
        clause
        for clause in document.clauses
        if any(
            marker in clause.text
            for marker in ("一切损失", "百分之三十的违约金", "30%的违约金", "负全责", "全部负责")
        )
    ]
    if not clauses:
        return findings
    findings.append(
        build_theme_finding(
            document=document,
            clauses=clauses,
            issue_type="one_sided_commercial_term",
            problem_title="商务责任和违约后果设置明显偏重",
            risk_level="high",
            severity_score=3,
            confidence="high",
            compliance_judgment="likely_non_compliant",
            why_it_is_risky=(
                "商务条款以“一切损失”“全部负责”或较高违约金比例等方式集中加重供应商责任。"
                "这类绝对化责任和高额后果设置容易突破合理风险分配边界。"
            ),
            impact_on_competition_or_performance="可能抬高供应商报价并扩大合同争议空间，降低潜在竞争参与意愿。",
            legal_or_policy_basis="中华人民共和国民法典；政府采购需求管理办法（财政部）",
            rewrite_suggestion="建议按过错、责任原因和损失范围细化违约责任，不宜使用绝对化责任表述或明显偏高的违约后果安排。",
            needs_human_review=True,
            human_review_reason="需结合合同风险分配、赔偿边界和违约责任比例判断相关责任条款是否明显失衡。",
            finding_origin="analyzer",
        )
    )
    return findings
