# 典型案例库样表

## 说明

本表用于沉淀可复用的典型案例，既服务于人工审查，也服务于后续评测集扩充。

## 字段定义

- `case_id`：案例编号
- `案例标题`：便于快速识别的名称
- `来源类型`：典型案例、投诉处理、内部样例、失败复盘
- `问题类型`：与 finding schema 中的 issue_type 对齐
- `采购方式`：公开招标、竞争性磋商、框架协议等
- `原始条款`：核心争议条款
- `问题概述`：一句话说明争议点
- `预期判断`：likely_non_compliant、potentially_problematic、likely_compliant、needs_human_review
- `严重度`：0-3
- `优先依据`：关联法规编号
- `reference_ids`：关联本地引用资料编号
- `source_url`：对应公开来源链接
- `建议改写方向`：如何改得更合规
- `是否进入评测集`：是/否
- `备注`：适用边界、是否需法域复核等

## 首批样例

| case_id | 案例标题 | 来源类型 | 问题类型 | 采购方式 | 原始条款 | 问题概述 | 预期判断 | 严重度 | 优先依据 | reference_ids | source_url | 建议改写方向 | 是否进入评测集 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CASE-001 | 属地分公司硬门槛 | 内部样例 | geographic_restriction | 公开招标 | 供应商须在采购人所在地行政区域内设有分公司，否则投标无效。 | 以属地设点作为准入门槛，可能不合理限制竞争 | likely_non_compliant | 3 | RULE-002、RULE-003 | CASESRC-005 | https://www.ccgp.gov.cn/llsw/202305/t20230515_19876700.htm | 改为本地化服务响应能力要求 | 是 | 高频问题 |
| CASE-002 | 奖项作为资格门槛 | 内部样例 | irrelevant_certification_or_award | 竞争性磋商 | 供应商须获得省级及以上质量奖项，否则资格不满足。 | 奖项通常与直接履约能力无当然关系 | likely_non_compliant | 3 | RULE-002、RULE-004 | CASESRC-001, CASESRC-006 | https://www.ccgp.gov.cn/llsw/202508/t20250827_25238222.htm | 删除奖项门槛，改为履约能力证明 | 是 | 高频问题 |
| CASE-003 | 同类业绩范围过宽 | 典型案例 | excessive_supplier_qualification | 公开招标 | 类似项目业绩包括财税咨询、培训、融资辅导、上市服务等。 | 同类业绩定义与采购标的不一致，可能扩大倾斜范围 | potentially_problematic | 2 | RULE-003、RULE-004 | CASESRC-002, CASESRC-007 | https://www.ccgp.gov.cn/llsw/202505/t20250513_24582811.htm | 仅保留与核心标的直接相关业绩 | 是 | 与评分标准联动 |
| CASE-004 | 平台功能过度外扩 | 内部样例 | brand_or_model_designation | 框架协议 | 供应商必须具备集业务、财务、税务、金融等服务为一体的云平台，并具备金融端、培训端、并购重组等功能。 | 采购标的为代理记账服务，但平台要求明显超出必要范围 | likely_non_compliant | 3 | RULE-003、RULE-005 | LEGAL-001, LEGAL-002 | https://www.mof.gov.cn/gkml/caizhengwengao/wg2021/wg202005/202109/P020210917565943122846.pdf | 缩减为与核心服务直接相关的平台能力 | 是 | 需结合项目标的判断 |
| CASE-005 | 评分标准主观打分过重 | 失败复盘 | ambiguous_requirement | 框架协议 | 根据现场陈述综合分析比较，在1-15分之间打分。 | 缺少量化标准，评审自由裁量过大 | potentially_problematic | 2 | RULE-004 | CASESRC-003 | https://www.ccgp.gov.cn/llsw/202401/t20240112_21420742.htm | 按分档标准拆解评分点 | 是 | 高频问题 |
| CASE-006 | 可量化服务响应要求 | 内部样例 | other | 公开招标 | 提供7×24小时支持，故障报修后2小时响应、24小时提供解决方案。 | 与履约直接相关且可量化 | likely_compliant | 0 | RULE-003 | LEGAL-001 | https://www.mof.gov.cn/gkml/caizhengwengao/wg2021/wg202005/202109/P020210917565943122846.pdf | 无需改写或仅作表述优化 | 否 | 用于反例训练 |
| CASE-007 | 资格条件重复转化为评分优势 | 内部样例 | duplicative_scoring_advantage | 公开招标 | 要求供应商具备注册会计师团队作为资格条件，同时按注册会计师人数重复加分。 | 资格条件被再次转化为评分优势，可能扭曲竞争 | potentially_problematic | 2 | RULE-004、RULE-012 | CASESRC-004 | https://www.ccgp.gov.cn/llsw/202511/t20251112_25678095.htm | 区分资格门槛与超出门槛的量化优势 | 是 | 需具体看分值设置 |
| CASE-008 | 主观评分缺少分档标准 | 典型案例 | ambiguous_requirement | 竞争性磋商 | 根据实施方案优劣综合比较打分，满分15分。 | 没有明确分档和判断基准，专家自由裁量大 | potentially_problematic | 2 | RULE-011、RULE-004 | CASESRC-003 | https://www.ccgp.gov.cn/llsw/202401/t20240112_21420742.htm | 细化为分项分档打分 | 是 | 高频投诉点 |
| CASE-009 | 本地服务机构作为资格门槛 | 内部样例 | geographic_restriction | 公开招标 | 供应商须在项目所在地设有固定服务机构，并提供属地备案证明。 | 将属地便利性直接转化为准入门槛，可能排除外地供应商 | likely_non_compliant | 3 | RULE-002、RULE-013 | CASESRC-005 | https://www.ccgp.gov.cn/llsw/202305/t20230515_19876700.htm | 改为中标后服务响应承诺或驻场机制 | 是 | 地域限制高频问题 |
| CASE-010 | AAA信用等级高权重加分 | 内部样例 | irrelevant_certification_or_award | 竞争性磋商 | 供应商具有AAA信用等级证书得5分，具有省级荣誉称号得5分。 | 奖项荣誉和信用等级可能与项目直接履约能力无关 | likely_non_compliant | 3 | RULE-010、RULE-014 | CASESRC-001, CASESRC-006 | https://www.ccgp.gov.cn/llsw/202508/t20250827_25238222.htm | 删除或大幅弱化此类加分项 | 是 | 高频争议点 |
| CASE-011 | 同类合同数量要求过高 | 内部样例 | excessive_supplier_qualification | 公开招标 | 供应商近三年须提供不少于5个同类项目合同，否则资格不满足。 | 同类业绩数量要求过高，可能不合理缩小竞争范围 | potentially_problematic | 2 | RULE-015、RULE-003 | CASESRC-002, CASESRC-007 | https://www.ccgp.gov.cn/llsw/202405/t20240524_22184337.htm | 缩减合同数量要求并明确同类范围 | 是 | 需结合项目特点论证 |
| CASE-012 | 验收标准仅写动态考核 | 内部样例 | unclear_acceptance_standard | 框架协议 | 采购人将对供应商开展动态绩效考核，不达标的取消资格。 | 缺少验收内容、标准、方法和记录机制 | potentially_problematic | 2 | RULE-016、RULE-003 | CASESRC-008, LEGAL-001 | https://www.ccgp.gov.cn/llsw/202304/t20230403_19643387.htm | 明确验收清单、考核指标和程序 | 是 | 履约争议高发点 |
| CASE-013 | 第三方付款前提条款 | 内部样例 | one_sided_commercial_term | 竞争性磋商 | 待上级资金拨付或第三方付款到账后，采购人再向供应商支付合同款。 | 将付款条件与第三方行为挂钩，增加供应商资金风险 | likely_non_compliant | 3 | RULE-017、RULE-008 | CASESRC-009 | https://www.ccgp.gov.cn/llsw/202506/t20250606_24726813.htm | 改为明确支付时点和逾期责任 | 是 | 中小企业风险高 |
| CASE-014 | 采购人绝对免责条款 | 内部样例 | one_sided_commercial_term | 框架协议 | 因项目实施产生的一切风险、损失及法律责任均由供应商承担，采购人不承担任何责任。 | 责任分配失衡，可能排除采购人法定或约定义务 | likely_non_compliant | 3 | RULE-017、RULE-008 | CASESRC-009 | https://www.ccgp.gov.cn/llsw/202506/t20250606_24726813.htm | 改为依法分别承担相应责任 | 是 | 合同条款高风险 |

## 维护建议

- 每新增一个公开案例，至少补齐 `问题类型`、`优先依据`、`建议改写方向` 三个字段。
- 每次发现智能体误判，都优先写入本表，再决定是否进入 benchmark。
