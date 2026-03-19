# 人工审查与代码审查差距矩阵

## 1. 文档目标

本文档用于把“人工审查具体怎么做”“当前代码审查已经覆盖到哪一层”“还缺哪些能力”整理成一张可持续复用的矩阵。

它服务三个目的：

- 帮助后续智能体快速理解人工审查的真实流程
- 帮助对齐代码审查当前已经覆盖到哪一步
- 帮助后续按步骤补模块，而不是继续零散补规则

本文档关注的是：

- 人工审查的操作流程
- 当前代码主链对这些步骤的覆盖程度
- 尚未补齐的关键缺口
- 建议优先补的模块

## 2. 当前总判断

当前代码审查已经不再只是“规则扫描器”，而是已经形成：

`文档解析 -> 文件级策略 -> 采购品目分类 -> 规则扫描 -> 主题分析器 -> 大模型关键节点介入 -> 仲裁归并 -> 证据选择 -> 法规语义 -> 导出与差异学习`

但它与人工审查的差距，已经从“看不见问题”收缩成：

- 场景理解还不够稳
- 结构性问题判断还不够强
- 边界分寸感还不够自然
- 改稿表达还不够成熟
- 跨章节联动还不够强
- engine 稳定性还在调优期

## 3. 人工审查流程与代码覆盖矩阵

| 人工审查步骤 | 人工具体会做什么 | 当前代码对应层 | 当前覆盖情况 | 主要缺口 | 建议优先补模块 |
| --- | --- | --- | --- | --- | --- |
| 1. 识别采购对象 | 先判断主标的、次标的、是否为混合采购，理解“到底采购什么” | `document_strategy_router`、`procurement_catalog_classifier`、`catalog_knowledge_profile` | 已覆盖到主品目、次品目、混合采购识别 | 细分场景理解仍不稳，轻量智能化、货物+服务边界易被带偏 | `catalog_knowledge_profile` 二阶段、`mixed_scope_boundary_engine` 二阶段 |
| 2. 判断采购阶段 | 判断当前文件是在需求形成、发布前复核、合同模板，还是其他阶段 | `procurement_stage_router` | 当前已聚焦“采购需求形成与发布前审查” | 仍缺更细粒度的阶段化差异策略 | `procurement_stage_router` 二阶段 |
| 3. 建立章节审查框架 | 先按资格、评分、技术、商务/验收建立检查框架 | `review_strategy`、章节分类、主题分析器 | 已覆盖 | 章节之间仍偏“分开审”，联动还不够强 | `cross_section_review_router` |
| 4. 识别显性问题 | 抓门槛、属地、品牌、错位证书、证明形式过严、单方责任等 | `rules/*`、`rule_scan`、`rule_registry` | 覆盖较强 | 规则治理和场景启停还不够成熟 | `rule_registry` 二阶段、`catalog_sensitive_rule_router` 二阶段 |
| 5. 判断结构性问题 | 看评分表是否失衡、商务链是否失衡、资格条件是否整体超范围 | `qualification_reasoning_engine`、`scoring_semantic_consistency_engine`、`commercial_lifecycle_analyzer` | 覆盖中等偏强 | 对“整张评分表”“整条商务链”的结构性理解还不够稳 | `scoring_semantic_consistency_engine` 二阶段、`commercial_lifecycle_analyzer` 二阶段 |
| 6. 做边界判断 | 区分“应删除”“应弱化”“需论证”“需复核” | `technical_necessity_explainer`、`confidence_calibrator`、法规语义层 | 已有雏形 | 分寸感还不够稳定，法律边界解释还不够像人工 | `confidence_calibrator` 二阶段、`legal_authority_reasoner` 二阶段 |
| 7. 收束成少数主问题 | 把碎点压成 5-10 条真正要改的章节主问题 | `finding_arbiter`、`theme_splitter_and_summarizer` | 已覆盖 | 有些项目仍过碎，或跨章节吞并过宽 | `finding_arbiter` 二阶段 |
| 8. 选择最有代表性的证据 | 挑最能支撑判断的那一两段原文，而不是把整章都塞进去 | `review_evidence`、品目感知证据选择 | 已覆盖 | 证据还不总是像人工挑出来的“最准那段” | `evidence_selector` 二阶段 |
| 9. 给出法规与适用逻辑 | 说明为什么这条法规适用、为什么这类问题需要改 | `legal_clause_index`、`issue_type_authority_map`、`legal_authority_reasoner` | 已覆盖第一版 | 仍偏“基础映射”，距离人工式法理表达还有差距 | `legal_authority_reasoner` 二阶段 |
| 10. 给出改稿意见 | 不是只说有问题，而是给采购人可直接修改的建议 | `rewrite_suggestion`、导出层、`review-check` | 已覆盖基础版 | 改稿表达还不够稳定、简洁、可直接替换 | `rewrite_generator`、导出模板二阶段 |
| 11. 做最终风险排序 | 判断哪些要先改、哪些需复核、哪些可后置优化 | 风险排序、`confidence_calibrator`、`review-check` | 已覆盖基础版 | 当前排序主要靠风险等级，仍缺“处理优先级”更细化逻辑 | `treatment_priority_router` |
| 12. 留下可复核结论 | 让采购人、法务、代理机构能复核和留痕 | `review_export`、`review-check`、`/rules` | 已覆盖 | benchmark 侧与采购人视角之间仍然偏分离 | `benchmark_regression_reporter` 二阶段、统一导出层 |

## 4. 当前最关键的差距类型

从整体架构和人工审查流程对照后，当前最关键的差距主要是 6 类。

### 4.1 场景理解还不够像人工

当前代码已经会做品目识别，但还不够稳定理解：

- 当前项目真正的履约核心是什么
- 哪些是合理配套
- 哪些是越界叠加
- 哪些只是轻量扩展而不应直接打成模板错贴

这意味着：

- 品目层已经有了
- 但“场景理解引擎”还没完全成熟

### 4.2 结构性判断还不够强

人工特别强的是看整体结构是否失衡，例如：

- 技术评分过重
- 团队、学历、证书、经验堆叠
- 商务条款把付款、考核、扣罚、解除串成单方链条

代码已经能看出一部分，但还不够稳定。

### 4.3 边界分寸感不足

人工会自然区分：

- 建议直接删除
- 建议弱化表述
- 建议补必要性论证
- 建议采购/法务复核

代码现在已经能输出这些标签，但判定边界还不够成熟。

### 4.4 改稿表达还不够成熟

代码已经能给出建议改写，但和人工相比还存在：

- 有时太抽象
- 有时不够像采购文本
- 有时不够利于直接替换

### 4.5 跨章节联动还不够自然

人工会自然把：

- 资格
- 评分
- 技术
- 商务/验收

几章联动起来理解。

代码现在章节内较强，但跨章节联动更多还是后处理，不够天然。

### 4.6 engine 稳定性还在调优期

当前系统已经进入“持续调 engine”的阶段：

- 品目识别偏差会放大全链误判
- 新 analyzer 上线后可能影响仲裁平衡
- 大模型节点收束还在继续控噪

## 5. 后续补强优先级

如果按“最像人工”来排，后续建议优先补这 5 组。

### P0

1. `catalog_knowledge_profile` 二阶段  
2. `scoring_semantic_consistency_engine` 二阶段  
3. `commercial_lifecycle_analyzer` 二阶段  
4. `finding_arbiter` 二阶段  
5. `confidence_calibrator` 二阶段  

### P1

1. `mixed_scope_boundary_engine` 二阶段  
2. `legal_authority_reasoner` 二阶段  
3. `evidence_selector` 二阶段  
4. `rewrite_generator` / 改稿建议增强  
5. `benchmark_regression_reporter` 二阶段  

### P2

1. 跨章节联动层  
2. 处理优先级路由层  
3. 统一交付层  

## 6. 使用建议

后续继续做“人工审查 vs 代码审查”对比时，建议不要只看：

- 命中了多少条
- 结果是不是变多了

而是按这张矩阵逐步判断：

- 当前是哪个步骤还弱
- 是识别弱、判断弱、收束弱，还是改稿表达弱
- 应该补规则、补 analyzer、补仲裁，还是补法规/证据/表达层

一句话说：

> 后续提升代码审查能力，最有效的方式已经不是继续单纯补规则，而是对照人工审查流程，一层层补齐“场景理解、结构判断、边界分寸、改稿表达和跨章节联动”。
