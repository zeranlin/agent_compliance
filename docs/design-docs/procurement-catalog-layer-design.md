# 采购品目目录层设计方案

## 目标

在现有代码审查主链路中补入“采购标的/品目标准化识别层”，先回答“这份文件采购的到底是什么”，再驱动后续规则、主题分析器、标的域匹配和混合场景边界判断。

目标不是单纯做一个分类器，而是让代码审查在以下方面更接近人工审查：
- 更准确识别资格错位、评分内容错位和模板错贴
- 更稳定判断混合采购场景边界
- 更自然区分“明显不当 / 需论证 / 可能合理”
- 为规则路由、主题分析器优先级和仲裁收束提供统一上游输入

## 背景问题

当前代码审查已经具备：
- 文档解析与标准化
- 高频显性规则命中
- 章节级主题分析器
- finding 仲裁与代表性证据选择
- 本地模型辅助扫描

但在真实文件中，仍会反复暴露一个共性问题：
- 代码往往先“看见某个词”，再判断是否有风险
- 缺少一层“先理解采购标的是什么”的标准化识别

这会带来几类典型偏差：
- 家具项目中把智能定位或系统支撑要求误判成纯模板错贴
- 药品项目中无法稳定区分合理配套自动化设备与越界信息化接口义务
- 标识标牌项目中把 IT/保安/信息安全认证仅当作错词，而无法结合项目品目判断其边界
- 物业、设备、信息化等项目中，规则和主题分析器的优先级缺少场景感

因此，当前主链路逻辑上确实少了一层：
- 采购标的标准化识别
- 品目知识映射
- 混合采购边界校准

## 设计原则

- 品目目录层服务于审查，不服务于“分类好看”
- 不把品目目录当成唯一真相，必须支持混合采购场景
- 先做最小可用集，不等待全量目录整理完成
- 输出必须可被 `document_strategy_router`、`domain_match_engine`、主题分析器直接消费
- 结果要同时支持规则路由、LLM 辅助提示和最终仲裁层

## 总体架构

建议在现有主链路中补入：

```text
document_strategy_router
  -> procurement_catalog_classifier
  -> domain_match_engine
  -> analyzers
  -> finding_arbiter
```

也可以更完整地看成：

```text
文档解析/标准化
  -> document_strategy_router
  -> procurement_catalog_classifier
  -> 品目知识映射
  -> domain_match_engine
  -> 高频规则层
  -> 主题分析器
  -> document_audit_llm
  -> finding_arbiter
  -> 输出
```

## 三层能力设计

### 一、品目分类层

先识别文件属于哪个或哪几个采购品目。

建议输出字段：
- `primary_catalog`
- `secondary_catalogs`
- `category_type`
- `catalog_confidence`
- `is_mixed_scope`
- `catalog_evidence`

其中：
- `primary_catalog`：主品目
- `secondary_catalogs`：次品目列表
- `category_type`：货物 / 服务 / 工程 / 混合
- `catalog_confidence`：置信度
- `is_mixed_scope`：是否为混合采购
- `catalog_evidence`：支撑该分类的标题、清单词、章节关键词等

分类输入可优先来自：
- 项目名称
- 招标公告标题
- 采购清单
- 技术要求关键词
- 评分标准关键词
- 商务章节关键词

### 二、品目知识层

对每个品目建立“合理要求画像”和“高风险画像”。

建议结构化字段：
- `catalog_id`
- `catalog_name`
- `category_type`
- `domain_keywords`
- `reasonable_requirements`
- `high_risk_patterns`
- `related_issue_types`
- `preferred_analyzers`

作用：
- 让系统知道该品目通常会出现什么
- 让系统知道什么要求对该品目属于高风险或高疑点
- 决定该文件应优先启用哪些规则和主题分析器

### 三、品目边界层

用于处理混合采购场景。

目标不是只说“混合”，而是判断：
- `合理配套`
- `需补充必要性论证`
- `边界不清`
- `明显错贴/义务外扩`

这层应与 `mixed_scope_boundary_engine`、`domain_match_engine` 协同工作。

## 最小可用品目集

不建议一开始追求全国全量覆盖，优先覆盖当前真实样本高频场景：

- 家具
- 窗帘 / 被服
- 物业管理服务
- 信息化平台 / 系统运维
- 医疗设备
- 药品及医用配套
- 标识标牌及宣传印制
- 设备供货并安装调试

原因：
- 这批场景已在真实文件中反复出现
- 现有规则、主题分析器和差异样本可直接反哺
- 可最快降低误判与漏判

## 数据结构建议

建议新增本地结构化数据文件：

`data/procurement-catalog/catalogs.json`

建议结构示例：

```json
[
  {
    "catalog_id": "CAT-FURNITURE",
    "catalog_name": "家具",
    "category_type": "goods",
    "domain_keywords": ["家具", "办公桌", "办公椅", "医用家具", "屏风", "柜体"],
    "reasonable_requirements": [
      "环保要求",
      "结构稳定性",
      "安装调试",
      "保修和维护"
    ],
    "high_risk_patterns": [
      "生产设备评分",
      "样品高分",
      "认证高分",
      "资产定位或智能管理边界外扩",
      "检测报告形式过严"
    ],
    "related_issue_types": [
      "scoring_content_mismatch",
      "technical_justification_needed",
      "one_sided_commercial_term"
    ],
    "preferred_analyzers": [
      "brand_and_certification_scoring_analyzer",
      "technical_reference_consistency_engine",
      "commercial_burden_analyzer"
    ]
  }
]
```

## 与现有模块的关系

### document_strategy_router

现有 `document_strategy_router` 负责根据整份文件生成主风险画像和优先复核路线。

引入品目目录层后：
- `document_strategy_router` 先输出场景级判断
- `procurement_catalog_classifier` 再输出主/次品目和混合标记
- 两者一起决定后续优先启用的分析器和关注章节

### domain_match_engine

当前 `domain_match_engine` 已能识别资格错位资质、评分错位证书、模板残留和义务外扩。

引入品目目录层后，应从“基于错位词”升级为“基于品目边界”：
- 当前采购主品目是什么
- 当前条款所属领域是什么
- 两者是匹配、需论证、边界不清还是明显错位

### 主题分析器路由

不同品目应优先启用不同分析器。

例如：

- 家具项目优先：
  - `brand_and_certification_scoring_analyzer`
  - `technical_reference_consistency_engine`
  - `commercial_burden_analyzer`

- 物业项目优先：
  - `personnel_certificate_mismatch_engine`
  - `commercial_lifecycle_analyzer`
  - `geographic_tendency_analyzer`

- 信息化项目优先：
  - `demo_mechanism_engine`
  - `scoring_semantic_consistency_engine`
  - 软件著作权、案例、驻场相关主题

- 标识标牌及宣传印制项目优先：
  - `scoring_semantic_consistency_engine`
  - `mixed_scope_boundary_engine`
  - `commercial_lifecycle_analyzer`

- 药品及医用配套项目优先：
  - `qualification_reasoning_engine`
  - `technical_reference_consistency_engine`
  - `mixed_scope_boundary_engine`
  - `commercial_burden_analyzer`

## 典型收益

引入后最直接的收益包括：

- 更准确识别资格错位
- 更准确识别评分内容错位
- 更准确识别模板错贴和义务外扩
- 更稳定判断混合采购场景边界
- 更准确地区分“合理配套 / 需论证 / 明显越界”
- 更合理安排规则和分析器的优先级
- 降低误报

## 风险与约束

### 1. 不把品目目录当成唯一真相

有些项目天然是混合采购，不能因为一个主品目就否定次品目要求。

因此必须支持：
- `primary_catalog`
- `secondary_catalogs`
- `is_mixed_scope`
- `catalog_confidence`

### 2. 不等待全量目录整理再上线

应先做“最小可用品目集”，覆盖当前真实文件高频场景。

### 3. 分类不是目标，审查变准才是目标

品目目录层的价值，不在于把文件分到一个漂亮标签，而在于：
- 让规则更准
- 让主题分析器更准
- 让仲裁层更稳

## 建议实施顺序

### P0

1. 新建设计与数据骨架
2. 实现 `procurement_catalog_classifier`
3. 建最小可用品目集
4. 把 `primary_catalog / secondary_catalogs / is_mixed_scope` 接到 `document_strategy_router`

### P1

1. 让 `domain_match_engine` 基于品目边界增强
2. 让主题分析器支持按品目路由
3. 为混合采购场景输出统一边界判断字段

### P2

1. 把差异学习结果反哺到品目知识层
2. 对高频品目持续扩展 `reasonable_requirements` 和 `high_risk_patterns`
3. 让 benchmark 覆盖品目分类与边界判断

## 与“2022政府采购品目分类目录”的关系

官方品目分类目录适合做这层的基础来源，但不建议直接机械照搬为审查规则。

更合适的做法是：
- 以官方目录为基础确定标准品目名称和层级
- 在仓库中建立“审查增强版品目知识映射”
- 用于审查的仍然是“品目 + 场景 + 风险画像”，而不是仅依赖目录编号

## 交付物建议

本方案落地后，建议新增或更新以下资产：

- `docs/design-docs/procurement-catalog-layer-design.md`
- `data/procurement-catalog/catalogs.json`
- `src/agent_compliance/knowledge/procurement_catalog.py`
- `src/agent_compliance/pipelines/strategy.py` 或 `document_strategy_router` 增强
- `tests/test_procurement_catalog.py`

## 结论

当前代码审查逻辑上确实少了一层“采购标的/品目标准化识别层”。

引入政府采购品目目录，不应只是增加一个分类表，而应形成：
- 品目分类层
- 品目知识层
- 品目边界层

这层能力一旦落入主链路，将直接提升：
- 错位判断
- 混合场景判断
- 规则路由
- 主题分析器优先级
- 最终章节主问题的准确性
