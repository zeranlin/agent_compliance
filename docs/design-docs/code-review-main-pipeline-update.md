# 代码审查主链路更新方案

## 目标

在已经引入采购品目目录层的前提下，正式更新代码审查主链路，让系统从“条款驱动审查”升级为“品目驱动 + 条款驱动审查”。

这次更新的目标不是再增加一个独立模块，而是重排主链路中的判断顺序，确保系统先回答：
- 这份文件采购的主标的是什么
- 属于哪个主品目、哪些次品目
- 是否属于混合采购场景
- 当前主风险更可能集中在哪些章节

再决定：
- 哪些规则优先命中
- 哪些主题分析器优先启用
- 哪些条款属于错位、越界或需论证
- 最终 findings 如何仲裁和收束

## 背景

当前代码审查已经具备：
- 文档解析与标准化
- 高频显性规则命中
- 章节级主题分析器
- 本地引用检索
- 本地模型辅助扫描
- finding 仲裁、证据选择与文件级摘要
- 采购品目目录分类器与最小可用品目集

但现有主链路仍保留明显的“旧顺序”特征：
- 先根据条款内容命中规则和主题
- 再在后处理阶段补文件级画像和品目摘要

这会导致：
- 品目层没有真正成为上游判断基础
- `domain_match_engine` 仍有一部分是“看见错位词再判断”
- 规则和主题分析器的启用优先级不够场景化
- 混合采购边界判断更多发生在后段，而不是前段路由

因此，当前确实需要对“代码审查主链路”做一次显式更新。

## 新主链路

建议将主链路更新为：

```text
文档解析与标准化
  -> document_strategy_router
  -> procurement_catalog_classifier
  -> catalog-aware clause routing
  -> rule scan
  -> domain_match_engine
  -> analyzers
  -> document_audit_llm
  -> finding_arbiter
  -> evidence_selector
  -> overall summary / output
```

对应到代码层，可以理解为：

```text
normalize
  -> review_strategy
  -> procurement_catalog
  -> review_findings / rule hits
  -> analyzers/*
  -> review_arbiter
  -> review_evidence
  -> render
```

## 新旧主链路差异

### 旧主链路

- 先看条款
- 先做规则命中
- 先做主题归并
- 最后补文件级画像和场景摘要

### 新主链路

- 先判断采购场景
- 先识别主/次品目和混合采购边界
- 再按品目路由规则和主题分析器
- 最后在仲裁层统一收束

一句话概括：

旧主链路更像“看到条款再猜项目”，  
新主链路更像“先知道项目是什么，再决定怎么审”。

## 各层职责

### 1. 文档解析与标准化层

职责：
- 提取正文
- 生成 `NormalizedDocument`
- 提供章节、条款、行号、表格和评分项定位基础

当前对应：
- `pipelines/normalize.py`
- `parsers/`

### 2. 文件级策略层

职责：
- 输出文件级风险画像
- 初步判断采购大类
- 给出优先复核路线

当前对应：
- `pipelines/review_strategy.py`

新增要求：
- 策略层不再只基于 findings 反推总结
- 要把品目分类结果纳入策略画像

### 3. 品目分类层

职责：
- 识别 `primary_catalog`
- 识别 `secondary_catalogs`
- 标记 `is_mixed_scope`
- 给出 `catalog_confidence`

当前对应：
- `knowledge/procurement_catalog.py`
- `data/procurement-catalog/catalogs.json`

新增要求：
- 分类结果必须进入后续规则和分析器路由
- 不再只是摘要文本里的附加说明

### 4. 品目路由层

职责：
- 按主品目决定规则优先级
- 按主/次品目决定主题分析器优先级
- 对混合采购场景提前加权 `mixed_scope_boundary_engine`

当前缺口：
- 这层还没有被明确抽象为独立逻辑

建议新增：
- `catalog-aware clause routing`

建议输出：
- `preferred_rules`
- `preferred_analyzers`
- `mixed_scope_priority`
- `catalog_routing_notes`

### 5. 高频规则层

职责：
- 命中高频显性问题
- 为主题分析器和 LLM 辅助提供候选条款

新增要求：
- 规则命中优先级应按品目调整
- 不同品目可使用不同的启发式过滤和加权

例子：
- 家具项目优先关注样品评分、环保检测、认证高分、售后响应
- 物业项目优先关注人员证书、驻场、考核、付款挂钩
- 信息化项目优先关注演示、软件著作权、案例、驻场和维护

### 6. 域匹配与边界判断层

职责：
- 判断条款与主品目是否匹配
- 判断混合采购场景是合理配套还是边界不清

对应模块：
- `domain_match_engine`
- `mixed_scope_boundary_engine`

新增要求：
- 从“错位关键词驱动”升级为“品目边界驱动”

判断结果建议统一为：
- `matched`
- `needs_justification`
- `boundary_unclear`
- `mismatched`

### 7. 主题分析器层

职责：
- 基于规则命中、章节结构和品目上下文生成章节级主问题

当前已存在的分析器包括：
- `qualification`
- `scoring`
- `technical`
- `commercial`
- `domain_match`
- `demo`
- `personnel`

新增要求：
- 各分析器应支持“按品目启用优先级”运行
- 部分分析器在某些品目中可弱化或跳过

例子：
- 家具项目：
  - 强启用：`brand_and_certification_scoring_analyzer`
  - 强启用：`technical_reference_consistency_engine`
  - 强启用：`commercial_burden_analyzer`
- 物业项目：
  - 强启用：`personnel_certificate_mismatch_engine`
  - 强启用：`commercial_lifecycle_analyzer`
  - 强启用：`geographic_tendency_analyzer`
- 信息化项目：
  - 强启用：`demo_mechanism_engine`
  - 强启用：`scoring_semantic_consistency_engine`
  - 强启用：软件著作权/案例/驻场类评分主题

### 8. LLM 辅助层

职责：
- 做局部边界判断
- 做章节级补点
- 做全文辅助扫描候选

新增要求：
- LLM prompt 也要感知主品目和混合场景
- 同一类问题在不同品目下，提示策略应不同

### 9. 仲裁与证据层

职责：
- 去重
- 压噪
- 主问题收束
- 代表性证据选择

对应模块：
- `review_arbiter.py`
- `review_evidence.py`

新增要求：
- 仲裁时参考主/次品目，避免跨场景误并
- 证据选择时优先保留与主品目直接相关的条款

## 需要新增或调整的字段

建议在 `ReviewResult` 或中间画像中补充：
- `primary_catalog`
- `secondary_catalogs`
- `catalog_confidence`
- `is_mixed_scope`
- `catalog_routing_notes`
- `preferred_analyzers`

同时在 `overall_risk_summary` 中统一输出：
- 主品目
- 次品目
- 混合采购提示
- 建议优先复核章节

## 对现有模块的影响

### review_strategy

需要更新为：
- 将品目分类结果纳入文件级策略画像
- 输出“建议复核路线 + 品目说明 + 混合场景说明”

### review.py

需要更新为：
- 主编排顺序显式改成“先策略、再品目、再规则/分析器”
- 让分析器调用不再是固定顺序，而是“基础顺序 + 品目加权顺序”

### analyzers/*

需要逐步支持：
- 读取主品目和次品目
- 根据品目判断是否增强、降权或跳过

### references_index

需要考虑：
- 让法规依据与案例引用也能挂品目或行业标签
- 后续便于按品目优先推荐依据

## 分阶段落地建议

### P0：主链路更新

目标：
- 让品目层成为主链路正式一环，而不是摘要附属信息

任务：
- 把 `procurement_catalog_classifier` 接入 `review_strategy`
- 在主编排中显式加入 `catalog-aware routing`
- 在 `overall_risk_summary` 中稳定输出品目与混合场景信息

### P1：分析器按品目路由

目标：
- 让规则和分析器真正按品目启用优先级

任务：
- 家具、物业、信息化、医疗设备、药品、标识标牌这几类先做
- 为各分析器加入 `catalog-aware` 入参

### P2：域匹配和 LLM 提示词升级

目标：
- 让错位判断和边界判断从“关键词式”升级为“品目边界式”

任务：
- 更新 `domain_match_engine`
- 更新 `mixed_scope_boundary_engine`
- 更新 LLM prompt 模板

### P3：评测和回归

目标：
- 验证品目层接入后是否真的降低误判、漏判

任务：
- 回归一批已处理文件
- 输出引入品目层前后的差异报告

## 成功标志

当以下结果稳定出现时，说明主链路更新成功：
- 家具项目不再轻易被当成信息化项目
- 药品项目中能更稳地区分合理配套自动化设备与越界接口义务
- 标识标牌项目中的 IT/保安/信息安全认证能稳定作为品目错位上浮
- 物业项目中的人员证书和考核条款不再与设备/信息化逻辑混淆
- `overall_risk_summary` 能先说明采购场景和建议复核路线，再展开具体问题

## 当前建议的下一步

1. 更新 `review.py` 的主编排顺序  
2. 在 `review_strategy.py` 中纳入品目分类结果  
3. 为 `qualification / scoring / technical / commercial` 四组分析器补 `catalog-aware` 入参  
4. 选 3 到 5 份已处理样本回归，验证误判是否下降
