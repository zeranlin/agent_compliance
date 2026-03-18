# review.py 模块化拆分方案

## 背景

当前代码审查主编排文件 [review.py](/Users/linzeran/code/2026-zn/agent_compliance/src/agent_compliance/pipelines/review.py) 已增长到 4000+ 行，内部同时承载了：

- 审查主入口
- 文档级风险画像
- 场景识别与复核路线
- 评分主题分析
- 资格主题分析
- 技术主题分析
- 商务主题分析
- 域匹配与混合场景判断
- 模板噪声过滤
- finding 仲裁、归并、去重
- 证据摘录与摘要生成

当前这种集中式实现可以快速试错，但继续沿用会带来几个问题：

- 单文件增强时容易把不同场景逻辑互相带坏
- 测试定位困难，改一个主题分析器时需要通读整份文件
- LLM 辅助、差异学习、规则候选等能力接入时，编排层职责越来越混杂
- 新增审查主题时，默认只能继续把逻辑堆进 `review.py`

因此需要在不破坏现有闭环节奏的前提下，把 `review.py` 从“功能堆栈文件”逐步拆回“主编排文件”。

## 目标

拆分后的目标不是“把所有函数挪走”，而是形成明确分层：

1. `review.py` 只保留主编排、阶段顺序和少量跨模块协调逻辑
2. 主题分析器按能力域拆到独立模块
3. 仲裁和证据选择形成可单测、可迭代的独立层
4. 文档级画像、场景路由、问题收束都能独立演进

## 当前职责切面

当前 `review.py` 大致包含 6 类职责：

### 1. 主编排职责

- `build_review_result`
- `_refine_findings`
- `_overall_summary`

这部分属于真正应该保留在主编排层的逻辑。

### 2. 文档级判断职责

- `_build_document_risk_profile`
- `_build_document_strategy_profile`
- `_document_domain`

这部分适合独立为“文件级判断层”。

### 3. 主题分析职责

包括但不限于：

- 评分：
  - `_add_scoring_structure_findings`
  - `_add_scoring_semantic_consistency_theme_finding`
  - `_add_personnel_scoring_theme_finding`
  - `_add_demo_mechanism_theme_finding`
  - `_add_business_strength_theme_finding`
  - `_add_brand_scoring_theme_finding`
  - `_add_certification_scoring_theme_finding`
  - `_add_property_service_experience_theme_finding`
- 资格：
  - `_add_qualification_bundle_findings`
  - `_add_qualification_financial_scale_theme_finding`
  - `_add_qualification_operating_scope_theme_finding`
  - `_add_qualification_industry_appropriateness_finding`
  - `_add_qualification_reasoning_theme_finding`
  - `_add_qualification_domain_theme_finding`
- 技术：
  - `_add_technical_reference_consistency_findings`
  - `_add_technical_standard_mismatch_theme_finding`
  - `_add_proof_formality_findings`
- 商务/验收：
  - `_add_commercial_chain_findings`
  - `_add_commercial_burden_findings`
  - `_add_payment_evaluation_chain_finding`
  - `_add_commercial_lifecycle_theme_finding`
  - `_add_acceptance_boundary_findings`
  - `_add_liability_balance_findings`
- 场景/域匹配：
  - `_add_domain_match_findings`
  - `_add_scoring_domain_theme_finding`
  - `_add_template_domain_theme_finding`
  - `_add_mixed_scope_boundary_theme_finding`
  - `_add_geographic_tendency_findings`
  - `_add_industry_appropriateness_findings`

这部分是最适合拆模块的主体。

### 4. 仲裁与去重职责

- `_drop_false_positive_findings`
- `_is_finding_covered_by_theme`
- `_drop_appendix_semantic_duplicates`
- `_is_semantic_duplicate_of_primary`
- `_matches_existing_signature`

这部分适合形成统一 `finding_arbiter` 模块。

### 5. 证据与表达职责

- `_build_theme_finding`
- `_build_theme_excerpt`
- `_shorten_section_path`
- `_shorten_segment`
- `_normalized_source_signature`

这部分适合形成 `evidence_selector` 与 `finding_renderer_helpers`。

### 6. 条款判定辅助职责

- `_is_qualification_clause`
- `_is_technical_clause`
- `_is_commercial_clause`
- `_is_substantive_commercial_clause`
- `_is_template_instruction_clause`
- `_is_scoring_clause`
- `_looks_like_supplier_level_qualification_clause`

这部分应逐步沉淀为共享的 clause classification utilities。

## 建议拆分后的目录

建议在 `src/agent_compliance/pipelines/` 下逐步形成：

```text
pipelines/
  review.py
  review_modules/
    __init__.py
    strategy.py
    clause_classification.py
    qualification.py
    scoring.py
    technical.py
    commercial.py
    domain_match.py
    arbiter.py
    evidence.py
```

### 各模块建议职责

#### `strategy.py`

负责：

- 文档域识别
- 文件级风险画像
- 文件级复核路线建议

拟迁移：

- `_document_domain`
- `_build_document_risk_profile`
- `_build_document_strategy_profile`

#### `clause_classification.py`

负责：

- 资格条款判断
- 评分条款判断
- 技术条款判断
- 商务条款判断
- 模板说明判断
- 供应商级资格门槛判断

拟迁移：

- `_is_qualification_clause`
- `_is_scoring_clause`
- `_is_technical_clause`
- `_is_commercial_clause`
- `_is_substantive_commercial_clause`
- `_is_template_instruction_clause`
- `_looks_like_supplier_level_qualification_clause`

#### `qualification.py`

负责：

- 资格门槛分层
- 资格错位资质
- 资格整体超范围判断

拟迁移：

- `_add_qualification_bundle_findings`
- `_add_qualification_financial_scale_theme_finding`
- `_add_qualification_operating_scope_theme_finding`
- `_add_qualification_industry_appropriateness_finding`
- `_add_qualification_reasoning_theme_finding`
- `_add_qualification_domain_theme_finding`

#### `scoring.py`

负责：

- 评分结构
- 评分语义一致性
- 品牌/认证/荣誉/经验/演示/人员证书

拟迁移：

- `_add_scoring_structure_findings`
- `_add_subjective_scoring_theme_finding`
- `_add_demo_mechanism_theme_finding`
- `_add_personnel_scoring_theme_finding`
- `_add_business_strength_theme_finding`
- `_add_scoring_semantic_consistency_theme_finding`
- `_add_service_scoring_mismatch_theme_finding`
- `_add_warranty_extension_scoring_theme_finding`
- `_add_software_copyright_scoring_theme_finding`
- `_add_experience_evaluation_theme_finding`
- `_add_property_service_experience_theme_finding`
- `_add_brand_scoring_theme_finding`
- `_add_certification_scoring_theme_finding`

#### `technical.py`

负责：

- 标准引用一致性
- 证明形式过严
- 技术需论证表达

拟迁移：

- `_add_technical_reference_consistency_findings`
- `_add_technical_standard_mismatch_theme_finding`
- `_add_proof_formality_findings`

#### `commercial.py`

负责：

- 商务链路
- 付款与履约评价绑定
- 验收费转嫁
- 责任失衡
- 验收边界

拟迁移：

- `_add_commercial_chain_findings`
- `_add_commercial_burden_findings`
- `_add_commercial_financing_burden_theme_finding`
- `_add_delivery_deadline_anomaly_theme_finding`
- `_add_commercial_acceptance_fee_shift_theme_finding`
- `_add_liability_imbalance_theme_finding`
- `_add_payment_evaluation_chain_finding`
- `_add_commercial_lifecycle_theme_finding`
- `_add_acceptance_boundary_findings`
- `_add_liability_balance_findings`

#### `domain_match.py`

负责：

- 标的域匹配
- 模板错贴
- 混合采购场景边界
- 属地倾斜
- 行业适配性

拟迁移：

- `_add_domain_match_findings`
- `_add_scoring_domain_theme_finding`
- `_add_template_domain_theme_finding`
- `_add_mixed_scope_boundary_theme_finding`
- `_add_geographic_tendency_findings`
- `_add_industry_appropriateness_findings`
- `_domain_mismatch_markers`

#### `arbiter.py`

负责：

- 假阳性过滤
- 主题覆盖判断
- 附件去重
- 跨章节归并控制

拟迁移：

- `_drop_false_positive_findings`
- `_is_finding_covered_by_theme`
- `_drop_appendix_semantic_duplicates`
- `_is_semantic_duplicate_of_primary`
- `_matches_existing_signature`
- `_is_appendix_duplicate_candidate`
- `_is_qualification_like_finding`
- `_is_scoring_finding`

#### `evidence.py`

负责：

- 代表性摘录
- 主题 finding 组装
- section path 收缩
- source signature

拟迁移：

- `_build_theme_finding`
- `_build_theme_excerpt`
- `_shorten_section_path`
- `_shorten_segment`
- `_normalized_source_signature`

## 拆分顺序

不建议一次性大拆。建议分 3 轮：

### 第一轮：先拆低风险公共层

目标：降低 `review.py` 基础密度，但不改业务结果。

优先拆：

1. `clause_classification.py`
2. `evidence.py`
3. `strategy.py`

原因：

- 这几层职责清楚
- 风险较低
- 对单文件闭环增强影响最小

完成标志：

- `review.py` 只保留对这些模块的调用
- 单元测试结果不变

### 第二轮：拆仲裁层

目标：把“收得像不像人工”这一层独立出来。

优先拆：

1. `arbiter.py`

原因：

- 现在大部分跨章节误并、模板污染、附件污染都在这里处理
- 这层独立后，后续增强会更可控

完成标志：

- 可单独为 `arbiter.py` 增加针对性单测
- `review.py` 不再自己维护大段过滤与覆盖判断

### 第三轮：按主题域拆分析器

目标：让后续“单文件闭环增强”不再往同一文件里堆函数。

优先顺序：

1. `scoring.py`
2. `commercial.py`
3. `qualification.py`
4. `domain_match.py`
5. `technical.py`

原因：

- 当前最频繁增强的是评分、商务、资格和域匹配
- 技术层现在复杂度相对略低，可稍后拆

## 与单文件闭环增强的关系

后续真实文件处理仍按既定闭环：

1. 人工审查
2. 代码审查
3. 差异对比
4. 归纳功能缺口
5. 先补显性规则
6. 再补主题分析器
7. 再补仲裁和证据选择
8. 回归当前文件
9. 再进下一份

模块拆分不应打断这个节奏。正确做法是：

- 在每轮文件闭环之外，穿插做小步拆分
- 每次只拆一个职责域
- 拆分后立即用现有真实样本回归

## 验证要求

每轮拆分至少满足：

- `tests.test_review_pipeline` 全通过
- 当前正在处理的真实样本回归结果主结论不倒退
- `review-next` 页面不需要改逻辑，只继续消费 `review` 结果

## 当前建议的下一步

按风险和收益排序，最适合马上开始的是：

1. 把 `clause_classification` 从 `review.py` 拆出
2. 把 `evidence_selector` 相关逻辑从 `review.py` 拆出
3. 把 `strategy` 从 `review.py` 拆出

这样能先把 `review.py` 从“全能大文件”降成“主编排 + 模块调用”，再继续做后续单文件闭环增强。
