# LGCG2025000102 人工逼近回归样本

## 文件

- `LGCG2025000102-A 龙岗区耳鼻咽喉医院迁址重建工程窗帘采购项目`

## 用途

用于验证代码审查是否逐步补齐以下人工高频查点：

- 资格条件中的不当企业属性、财务门槛、属地限制、类似业绩前置
- 评分项中的本地业绩、本地服务机构、本地团队加分
- 样品、认证、业绩等多类高分因素叠加
- 商务责任失衡、单方解除、违约金、扣款条件
- 抽检、复检、验收、付款链路
- 技术要求中的“需论证”中间层判断

## 预期重点命中

### 资格条件

- `expected_issue_types`: `excessive_supplier_qualification`, `geographic_restriction`

- `excessive_supplier_qualification`
  - 主管单位同意函
  - 年收入/注册资本/年平均盈利
  - 国有资本持股比例
  - 连续多年审计报告
  - 国家级特色企业
- `geographic_restriction`
  - 本地机构、本地团队、本地注册或类似属地门槛
- `excessive_supplier_qualification`
  - 类似业绩被前置为资格条件时，应形成独立问题点

### 评分标准

- `expected_issue_types`: `duplicative_scoring_advantage`, `geographic_restriction`, `excessive_scoring_weight`, `scoring_structure_imbalance`, `post_award_proof_substitution`

- `duplicative_scoring_advantage`
  - 资格材料或营业执照被重复转评分
- `geographic_restriction`
  - 本地业绩、本地服务机构、本地团队加分
- `excessive_scoring_weight`
  - 样品高分
  - 认证高分
  - 业绩高分
- `scoring_structure_imbalance`
  - 样品、认证、业绩多类高分因素集中出现

### 商务、验收、付款

- `expected_issue_types`: `one_sided_commercial_term`, `unclear_acceptance_standard`, `payment_acceptance_linkage`

- `one_sided_commercial_term`
  - 采购人绝对免责
  - 一切事故全部由供应商承担
  - 单方解除合同
  - 违约金或扣款条件过重
- `unclear_acceptance_standard`
  - 抽检、复检、整改、复验边界不清
- `payment_acceptance_linkage`
  - 抽检终验与付款绑定
  - 财政资金或内部审批与付款绑定

### 技术要求

- `expected_issue_types`: `narrow_technical_parameter`, `technical_justification_needed`

- `narrow_technical_parameter`
  - 兼容性、接口、平台、定向参数
- `technical_justification_needed`
  - 安全环保类技术要求需论证
  - 检测证明形式和报告时效需论证

## 当前回归关注点

1. 结果是否仍能覆盖上述主要查点
2. 技术“需论证”类 finding 是否开始按主题归并，而不是碎片化刷屏
3. 商务责任失衡是否从泛化 finding 变为责任、验收、付款链路各自清晰
4. 评分项中的属地限制是否不再漏报

## 差异标签建议

- `missed_geographic_scoring_issue`
- `missed_past_performance_qualification_issue`
- `missed_contract_termination_issue`
- `missed_penalty_deduction_issue`
- `over_fragmented_technical_justification`
- `over_merged_business_chain_issue`
