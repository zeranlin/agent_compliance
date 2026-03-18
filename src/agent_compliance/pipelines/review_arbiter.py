from __future__ import annotations

from agent_compliance.schemas import Finding


def renumber_findings(findings: list[Finding]) -> list[Finding]:
    for index, finding in enumerate(findings, start=1):
        finding.finding_id = f"F-{index:03d}"
    return findings


def sort_findings(findings: list[Finding]) -> list[Finding]:
    priority = {"high": 0, "medium": 1, "low": 2, "none": 3}
    return sorted(
        findings,
        key=lambda item: (
            priority.get(item.risk_level, 9),
            item.text_line_start,
            item.text_line_end,
            item.issue_type,
            item.problem_title,
        ),
    )


def apply_finding_arbiter(findings: list[Finding]) -> list[Finding]:
    theme_findings = [finding for finding in findings if finding.finding_origin == "analyzer"]
    if not theme_findings:
        return findings

    filtered: list[Finding] = []
    for finding in findings:
        if finding.finding_origin == "analyzer":
            filtered.append(finding)
            continue
        if is_finding_covered_by_theme(finding, theme_findings):
            continue
        filtered.append(finding)
    return filtered


def is_finding_covered_by_theme(finding: Finding, themes: list[Finding]) -> bool:
    for theme in themes:
        if theme_covers_finding(theme, finding):
            return True
    return False


def theme_covers_finding(theme: Finding, finding: Finding) -> bool:
    if not line_ranges_overlap(theme, finding, tolerance=4):
        return False

    title = theme.problem_title
    if "多个方案评分项大量使用主观分档且缺少量化锚点" in title:
        return finding.issue_type == "ambiguous_requirement" and is_scoring_finding(finding)

    if "现场演示分值过高且签到要求形成额外门槛" in title:
        return finding.issue_type in {
            "ambiguous_requirement",
            "excessive_scoring_weight",
            "geographic_restriction",
        } and text_contains_any(
            finding,
            ("演示", "原型", "PPT", "视频", "签到", "60分钟", "60 分钟", "得 0 分"),
        )

    if "样品评分叠加递交签到和不接收机制形成额外门槛" in title:
        return finding.issue_type in {
            "ambiguous_requirement",
            "excessive_scoring_weight",
            "geographic_restriction",
            "other",
        } and text_contains_any(
            finding,
            ("样品", "签到", "不予签到", "样品不予接收", "授权委托书", "签到地点", "9:00-9:30", "14:00-14:30"),
        )

    if "生产设备和制造能力直接高分赋值且与核心履约评价边界不清" in title:
        return finding.issue_type in {
            "excessive_scoring_weight",
            "scoring_content_mismatch",
        } and text_contains_any(
            finding,
            ("生产设备", "数控剪板机", "自动化生产线", "异性海绵切割机", "购买发票", "租赁设备"),
        )

    if "人员与团队评分混入错位证书并过度堆叠条件" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "irrelevant_certification_or_award",
            "excessive_scoring_weight",
        } and text_contains_any(
            finding,
            ("项目负责人", "项目团队", "职称", "证书", "奖项", "荣誉", "项目经验", "特种设备"),
        )

    if "商务评分将企业背景和一般财务能力直接转化为高分优势" in title:
        return finding.issue_type in {
            "excessive_supplier_qualification",
            "excessive_scoring_weight",
            "scoring_content_mismatch",
            "irrelevant_certification_or_award",
        } and text_contains_any(
            finding,
            ("注册资本", "营业收入", "净利润", "标准", "标准委员会", "驰名商标", "著名商标", "名牌产品", "品牌价值"),
        )

    if "评分项名称、内容和评分证据之间不一致" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "excessive_supplier_qualification",
            "irrelevant_certification_or_award",
            "technical_justification_needed",
        } and text_contains_any(
            finding,
            (
                "工程案例",
                "CMA",
                "检测报告",
                "资产总额",
                "营业收入",
                "净利润",
                "标准委员会",
                "ISO20000",
                "先进单位",
                "注册安全工程师",
                "商品包装",
                "快递包装",
                "IT服务管理体系认证",
                "保安服务认证",
                "信息安全管理体系认证",
                "软件著作权",
                "UV 打印机",
                "喷绘机",
                "写真机",
                "雕刻机",
                "折弯机",
            ),
        )

    if "售后服务评分混入荣誉证书且主观分值偏高" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "irrelevant_certification_or_award",
            "ambiguous_requirement",
        } and text_contains_any(
            finding,
            ("先进单位", "注册安全工程师", "售后服务方案", "方案极合理", "产品升级", "配品配件"),
        )

    if "售后服务评分混入业绩、荣誉和资格材料" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "duplicative_scoring_advantage",
            "irrelevant_certification_or_award",
            "excessive_scoring_weight",
        } and text_contains_any(
            finding,
            ("售后服务", "医疗行业", "守合同重信用", "科技型中小企业", "营业执照", "事业单位法人证书"),
        )

    if "免费质保期延长按年度直接高分赋值" in title:
        return finding.issue_type in {
            "excessive_scoring_weight",
            "ambiguous_requirement",
        } and text_contains_any(
            finding,
            ("免费质保期", "延长1年", "延长 1 年", "得100分", "最高100分"),
        )

    if "软件著作权评分过高且与履约能力评价边界不清" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "excessive_scoring_weight",
            "irrelevant_certification_or_award",
        } and text_contains_any(
            finding,
            ("软件著作权", "著作权登记证书", "资产管理读写基站", "城市大数据服务运营类", "城市公共信息服务云类"),
        )

    if "经验评价叠加主观履约评价证明且分值过高" in title:
        return finding.issue_type in {
            "excessive_scoring_weight",
            "scoring_content_mismatch",
        } and text_contains_any(
            finding,
            ("履约评价为满意", "履约评价为优秀", "其他同等评价", "国家机关或事业单位委托", "项目经验", "医院物业", "三甲医院", "评审创建", "复审经验"),
        )

    if "医院物业经验和医院评审经验评分高权重且叠加履约评价证明" in title:
        return finding.issue_type in {
            "excessive_scoring_weight",
            "scoring_content_mismatch",
        } and text_contains_any(
            finding,
            ("医院物业", "三甲医院", "评审创建", "复审经验", "履约评价为满意", "履约评价为优秀", "总体履约评价结果"),
        )

    if "付款条件与履约评价结果深度绑定且评价标准开放" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "other",
        } and text_contains_any(
            finding,
            ("履约评价", "阶段款", "支付", "评价标准", "评价指标", "解除合同", "扣款", "管理费直接挂钩", "并非最终版本", "无条件服从", "满意度调查"),
        )

    if "履约全链路中的付款、验收、责任和到场响应边界整体偏向供应商承担" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "unclear_acceptance_standard",
            "geographic_restriction",
            "other",
        } and text_contains_any(
            finding,
            ("付款", "验收", "送检", "检测", "专家评审", "24小时", "2小时", "12小时", "48小时", "到场", "解除合同", "实际需求", "质保期", "售后服务保证金", "开机率", "备用设备", "财政审批", "暂停支付"),
        )

    if "资格条件中存在与标的域不匹配的资质或登记要求" in title:
        return finding.issue_type == "qualification_domain_mismatch"

    if "资格条件中存在与标的域不匹配的行业资质或专门许可" in title:
        return finding.issue_type in {"qualification_domain_mismatch", "excessive_supplier_qualification"} and text_contains_any(
            finding,
            ("水运工程监理", "有害生物防制", "SPCA", "特种设备"),
        )

    if "资格条件设置一般财务和规模门槛" in title:
        return finding.issue_type in {
            "excessive_supplier_qualification",
        } and text_contains_any(
            finding,
            ("纳税", "员工总数", "资产总额", "参保人数", "月均参保", "社保", "注册资本", "年收入", "净利润"),
        )

    if "资格条件设置经营年限、属地场所或单项业绩门槛" in title:
        return finding.issue_type in {
            "qualification_domain_mismatch",
            "excessive_supplier_qualification",
            "geographic_restriction",
        } and text_contains_any(
            finding,
            ("成立日期", "成立时间", "高新区", "固定的售后服务场所", "单项合同金额", "经营地址", "主城四区", "福州市", "经营年限", "外商投资及民营企业", "上级主管单位", "审计报告", "国家级特色企业"),
        )

    if "资格条件整体超出法定准入和履约必需范围" in title:
        return finding.issue_type in {
            "excessive_supplier_qualification",
            "qualification_domain_mismatch",
            "geographic_restriction",
        } and text_contains_any(
            finding,
            ("纳税", "参保人数", "员工总数", "资产总额", "成立日期", "固定的售后服务场所", "经营地址", "单项合同金额", "有害生物防制", "SPCA", "棉花加工资格", "水运工程监理", "注册资本", "年收入", "净利润", "股权结构", "经营年限", "高新技术企业", "外商投资及民营企业", "上级主管单位", "审计报告", "国家级特色企业"),
        )

    if "评分项直接按品牌档次赋分" in title:
        return finding.issue_type in {"brand_or_model_designation", "scoring_content_mismatch"} and text_contains_any(
            finding,
            ("一线品牌", "国际知名品牌", "格力", "美的", "海尔", "大金", "日立"),
        )

    if "认证评分混入错位证书且高分值结构失衡" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "irrelevant_certification_or_award",
            "scoring_structure_imbalance",
        } and text_contains_any(
            finding,
            ("高空清洗", "CCRC", "ISO20000", "认证证书", "体系认证", "生活垃圾分类", "售后服务认证", "五星售后", "商品售后服务评价", "环境标志产品", "节能产品"),
        )

    if "认证评分项目过密且高分值集中" in title:
        return finding.issue_type in {
            "excessive_scoring_weight",
            "post_award_proof_substitution",
            "technical_justification_needed",
        } and text_contains_any(
            finding,
            ("质量管理体系认证", "环境管理体系认证", "职业健康安全管理体系认证", "低VOCs", "有害物质限量", "抗菌", "防霉", "中标（成交）后4个月内取得", "取得以上认证证书"),
        )

    if "评分项中存在与标的域不匹配的证书认证或模板内容" in title:
        return finding.issue_type == "scoring_content_mismatch" and is_scoring_finding(finding)

    if "技术要求中混入与标的不匹配的标准引用和检测报告形式限制" in title:
        return finding.issue_type in {"technical_justification_needed", "template_mismatch", "scoring_content_mismatch"} and text_contains_any(
            finding,
            ("QB/T", "CMA", "本市具有检验检测机构", "权威质检部门", "检测报告原件扫描件", "2022 年起"),
        )

    if "技术要求引用了与标的不匹配的标准或规范" in title:
        return finding.issue_type in {"technical_justification_needed", "template_mismatch", "scoring_content_mismatch"} and text_contains_any(
            finding,
            ("QB/T", "GB 6249", "GB 15605", "QB/T 1649", "QB/T 4089", "空气质量检测装置", "菜肴罐头", "聚苯乙烯泡沫包装材料"),
        )

    if "技术证明材料形式要求过严且带有地方化限制" in title:
        return finding.issue_type in {"technical_justification_needed", "template_mismatch", "scoring_content_mismatch"} and text_contains_any(
            finding,
            ("本市具有检验检测机构", "带有 CMA", "带有CMA", "权威质检部门", "检测报告原件扫描件", "2022 年起", "国家级检测中心", "检验报告", "相关检测报告"),
        )

    if "文件中存在与标的域不匹配的模板残留或义务外扩" in title:
        if "设备采购场景叠加信息化接口和碳足迹义务，边界不清" in finding.problem_title:
            return False
        return (
            finding.issue_type in {"template_mismatch", "other"}
            and not is_qualification_like_finding(finding)
            and not text_contains_any(
                finding,
                ("软件端口", "医院信息系统", "HIS", "PACS", "LIS", "数据交换", "碳足迹", "改进报告"),
            )
        )

    if "混合采购场景叠加自动化设备和信息化接口义务，边界不清" in title:
        return finding.issue_type in {"template_mismatch", "other", "technical_justification_needed"} and text_contains_any(
            finding,
            ("信息化管理系统", "系统端口", "无缝对接", "综合业务协同平台", "自动化调剂", "发药机", "药瓶清洁", "系统进行管理维护"),
        )

    if "标识标牌及宣传印制服务叠加设备保障和信息化支撑内容，边界不清" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "technical_justification_needed",
            "template_mismatch",
            "other",
            "irrelevant_certification_or_award",
        } and text_contains_any(
            finding,
            ("软件著作权", "UV 打印机", "UV打印机", "喷绘机", "写真机", "雕刻机", "折弯机", "系统端口", "无缝对接"),
        )

    if "商务条款叠加设置异常资金占用、交货期限和责任负担" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "unclear_acceptance_standard",
            "other",
        } and text_contains_any(
            finding,
            ("履约担保", "备用金", "1000", "报验", "送检", "专家评审", "百分之三十", "一切损失"),
        )

    if "商务条款设置异常资金占用安排" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "other",
        } and text_contains_any(
            finding,
            ("履约担保", "备用金", "售后服务保证金", "质保期结束", "现金形式", "5%", "36个月", "自动转为质保保证金", "质保期满后无息退还", "履约保证金不予退还"),
        )

    if "交货期限设置异常或明显失真" in title:
        return finding.issue_type in {"one_sided_commercial_term", "other"} and text_contains_any(
            finding,
            ("1000", "交货"),
        )

    if "验收送检、检测和专家评审费用整体转嫁给供应商" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "unclear_acceptance_standard",
            "other",
        } and text_contains_any(
            finding,
            ("报验", "送检", "检测报告", "专家评审", "自行消化", "空气检测", "监理", "整改费用", "复验费用", "抽检费用"),
        )

    if "商务责任和违约后果设置明显偏重" in title:
        return finding.issue_type in {
            "one_sided_commercial_term",
            "payment_acceptance_linkage",
            "other",
        } and text_contains_any(
            finding,
            ("一切损失", "违约金", "30%", "百分之三十", "负全责", "全部负责", "不承担任何责任", "扣除全部履约保证金", "直接扣减合同价款"),
        )

    if "验收程序、复检与最终确认边界不清" in title:
        return finding.issue_type in {
            "unclear_acceptance_standard",
            "one_sided_commercial_term",
            "other",
        } and text_contains_any(
            finding,
            ("验收报告", "最终验收结果", "复检", "技术验收", "商务验收", "开箱检验"),
        )

    if "驻场、短时响应或服务场地要求形成事实上的属地倾斜" in title:
        return finding.issue_type in {"geographic_restriction", "personnel_restriction"} and text_contains_any(
            finding,
            ("1小时", "1 小时", "60分钟", "60 分钟", "2小时", "2 小时", "4小时", "4 小时", "12小时内提供备件", "24小时内到场", "高新区内", "固定的售后服务场所", "驻场", "现场服务", "本地售后网点", "驻点服务站", "本地备件库"),
        )

    if "评分和技术要求中存在行业适配性不足的错位内容" in title:
        return finding.issue_type in {
            "scoring_content_mismatch",
            "technical_justification_needed",
            "template_mismatch",
            "qualification_domain_mismatch",
        } and text_contains_any(
            finding,
            ("水运工程监理", "高空清洗", "CCRC", "ISO20000", "空气质量检测装置", "菜肴罐头"),
        )

    if "评分结构中多类高分因素集中出现" in title:
        return finding.issue_type == "excessive_scoring_weight"

    if "设备采购场景叠加信息化接口和碳足迹义务，边界不清" in title:
        return finding.issue_type in {"template_mismatch", "other", "technical_justification_needed"} and text_contains_any(
            finding,
            ("软件端口", "医院信息系统", "HIS", "PACS", "LIS", "数据交换", "碳足迹", "改进报告"),
        )

    return False


def line_ranges_overlap(left: Finding, right: Finding, *, tolerance: int = 0) -> bool:
    return not (
        left.text_line_end + tolerance < right.text_line_start
        or right.text_line_end + tolerance < left.text_line_start
    )


def text_contains_any(finding: Finding, markers: tuple[str, ...]) -> bool:
    haystack = " ".join(
        part
        for part in (
            finding.problem_title,
            finding.source_text,
            finding.section_path or "",
            finding.source_section or "",
        )
        if part
    )
    return any(marker in haystack for marker in markers)


def is_scoring_finding(finding: Finding) -> bool:
    haystack = " ".join(part for part in (finding.section_path or "", finding.source_section or "") if part)
    return "评标信息" in haystack or "评分" in haystack


def is_qualification_like_finding(finding: Finding) -> bool:
    haystack = " ".join(
        part for part in (finding.section_path or "", finding.source_section or "", finding.source_text or "") if part
    )
    return any(marker in haystack for marker in ("申请人的资格要求", "资格条件", "生活垃圾分类服务认证证书", "公司治理评级证书", "合规管理体系认证证书"))
