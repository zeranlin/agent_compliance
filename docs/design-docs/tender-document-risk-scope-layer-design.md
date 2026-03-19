# 招标文件业务结构识别与风险作用域判定层设计

## 背景

当前代码审查已经开始补：

- 品目与场景理解层
- `effective_requirement_scope_filter`
- `requirement_scope_layer`

这些能力已经能在“条款级”上做：

- 正文 / 模板 / 提示 / 格式 区分
- 条款功能识别
- 条款效力强弱识别

但真实文件复跑暴露出一个更上游的缺口：

- 代码审查在进入条款级判断前，尚未稳定识别“整份招标文件在业务结构上由哪些部分组成”
- 也尚未回答“这份招标文件里，哪些部分是当前采购需求风险审查真正要重点看的作用域”

这会导致系统仍然容易出现以下问题：

1. 把整份招标文件正文都当成同权重风险来源
2. 把资格性审查表、符合性审查表、评标办法说明、招标公告信息和真正的采购需求正文混在一起看
3. 把程序性条款、格式样表和实质采购需求条款混入同一主问题生成链路

因此，当前需要在 `normalize` 和 `requirement_scope_layer` 之间，再补一层更上游的：

- `tender_document_risk_scope_layer`

## 目标

这一层的目标不是直接生成风险结论，而是先从业务结构上识别：

1. 这份文件内部有哪些业务板块
2. 每个板块在政府采购招标文件里承担什么作用
3. 对“采购需求合规性审查智能体”来说，哪些板块属于：
   - 核心风险审查范围
   - 辅助风险审查范围
   - 非当前审查重点

一句话：

- **先找出真正需要审查风险的内容，再进入条款级风险识别**

## 非目标

第一版不做：

- 全量招标文件类型学研究
- 完整的交易程序合规审查系统
- 发布后争议裁判
- 仅靠这一层直接下 risk finding

这层只服务：

- 当前“采购需求形成、修改、复核和发布前”场景下的风险识别

## 设计原则

### 1. 先识别文件结构，再识别条款语义

这层解决的是：

- “这个章节/区块是什么”

而 `requirement_scope_layer` 解决的是：

- “这段 clause 起什么作用、效力多强”

两层不能混为一谈。

### 2. 先识别风险作用域，再决定是否高权重进入下游

不是所有招标文件内容都应该同等进入：

- 规则扫描
- 混合边界判断
- 评分语义判断
- 商务链路判断

必须先做风险作用域分层。

### 3. 业务结构识别优先于关键词零散命中

例如：

- “资格性审查表”里的资格项
- “评标信息”里的评分项
- “合同条款”里的付款验收责任

即使出现相似词，也不能脱离它所在板块的业务角色来判断。

### 4. 先做高价值结构块，不做全量过拟合

第一版只覆盖当前最影响采购需求风险识别质量的结构块。

## 在主链中的位置

建议新主链调整为：

```text
normalize
-> tender_document_risk_scope_layer
-> requirement_scope_layer
-> procurement_stage_router / strategy / catalog
-> rule governance / rule scan
-> analyzers
-> llm nodes
-> finding_arbiter
-> evidence / output
```

也就是：

- `normalize`
  - 把文档切成 clause，并保留 section_path
- `tender_document_risk_scope_layer`
  - 识别 clause 所在的业务结构块和风险作用域
- `requirement_scope_layer`
  - 在各结构块内部继续做条款功能和效力分层

## 第一版结构标签

### 一、document_structure_type

第一版建议先识别这些结构块：

- `notice_info`
  - 公告信息、项目基本信息、采购人/代理机构信息、时间地点
- `bidder_instructions`
  - 投标人须知、程序性要求、投标文件编制要求
- `qualification_review`
  - 资格性审查表、资格要求、准入条件
- `conformity_review`
  - 符合性审查表、实质性响应检查
- `scoring_rules`
  - 评分标准、评分项、综合评分、评标信息
- `technical_requirements`
  - 用户需求书、技术参数、技术指标、配置要求
- `commercial_requirements`
  - 商务要求、交付、售后、响应、付款、违约
- `acceptance_requirements`
  - 验收、送检、复检、测试、专家评审、最终确认
- `contract_terms`
  - 合同条款、责任、付款、解除、赔偿
- `attachments_templates`
  - 投标函、承诺函、声明函、授权书、附件样表

### 二、risk_scope

第一版建议先定义三档风险作用域：

- `core_risk_scope`
  - 当前采购需求风险识别的核心对象
- `supporting_risk_scope`
  - 可以辅助判断，但不应与核心内容同权
- `out_of_scope`
  - 当前场景下不应高权重进入采购需求风险判断

### 三、scope_reason

建议给每个结构块打一个简短原因，例如：

- `属于评分标准正文，直接影响评审逻辑`
- `属于资格性审查块，可能转化为实质准入门槛`
- `属于程序说明或格式附件，不属于当前风险主判断范围`

## 风险作用域定义

### core_risk_scope

第一版建议这些结构块直接进核心风险作用域：

- `qualification_review`
- `scoring_rules`
- `technical_requirements`
- `commercial_requirements`
- `acceptance_requirements`
- `contract_terms`

原因：

- 它们最直接承载采购需求风险
- 是采购人发布前最应修改和复核的内容

### supporting_risk_scope

第一版建议这些结构块作为辅助作用域：

- `conformity_review`
- `bidder_instructions`

原因：

- 有时会嵌入实质性限制竞争或程序性偏差
- 但通常不应与采购需求正文完全同权

### out_of_scope

第一版建议这些结构块默认低权重或排除：

- `notice_info`
- `attachments_templates`

原因：

- 多数为公告信息、格式样表、承诺模板
- 容易污染风险识别，但不是当前“采购需求风险审查”的主对象

## 与 requirement_scope_layer 的关系

这两层是上下游关系，不是替代关系。

### tender_document_risk_scope_layer 回答的问题

- 这一段 clause 所属的业务结构块是什么
- 它处在什么风险作用域里

### requirement_scope_layer 回答的问题

- 这一段 clause 在所在结构块中起什么作用
- 它的约束强度有多高

可以这样理解：

```text
业务结构层：
  这段话属于“评分标准”还是“格式附件”？

条款语义层：
  它在评分标准里是评分因素、评分证据，还是说明性文字？
  它是强约束条款还是参考性表述？
```

### 组合后的完整判断

后续引擎应该优先基于：

- `document_structure_type`
- `risk_scope`
- `scope_type`
- `clause_function`
- `effect_strength`

一起判断，而不是只看某一个关键词。

## 第一版如何接回主链

### 1. 接在 normalize 之后

`run_normalize()` 完成后，先为 clause 打：

- `document_structure_type`
- `risk_scope`
- `scope_reason`

然后再进入 `requirement_scope_layer`

### 2. review.py

第一版建议在这些地方先消费：

- 初始 RuleHit -> Finding 组装前
  - 降权或跳过 `out_of_scope`
- `mixed_scope_boundary_engine`
  - 只优先看 `core_risk_scope` 和一部分 `supporting_risk_scope`
- `commercial_lifecycle_analyzer`
  - 优先看 `commercial_requirements / acceptance_requirements / contract_terms`
- `scoring_semantic_consistency_engine`
  - 优先看 `scoring_rules`

### 3. finding_arbiter

第一版建议：

- 当某个 finding 主要来源于 `out_of_scope` 结构块时，不应轻易上浮为主问题
- 当同一主题同时有 `core_risk_scope` 与 `supporting_risk_scope` 证据时，应优先保留核心结构块证据

### 4. review_evidence

第一版建议：

- 代表性证据优先选 `core_risk_scope`
- 若只有 `supporting_risk_scope`，可保留，但要弱化其作为主证据的优先级

## 第一版落地范围

第一版不直接追求全量智能分类，先做最有价值的范围。

### 范围一：先按章节标题和 section_path 启发式识别结构块

先不做复杂模型分类，优先用：

- `section_path`
- `source_section`
- `table_or_item_label`
- 常见标题词

完成 `document_structure_type` 初步识别。

### 范围二：先覆盖最常见的 10 类结构块

就按前面那 10 类先做。

### 范围三：只先做 3 档风险作用域

- `core_risk_scope`
- `supporting_risk_scope`
- `out_of_scope`

### 范围四：优先接 4 个最关键模块

- `review.py`
- `scoring_semantic_consistency_engine`
- `mixed_scope_boundary_engine`
- `commercial_lifecycle_analyzer`
- `finding_arbiter`
- `review_evidence`

## 第一版预期收益

补上这一层后，直接收益包括：

1. 不再把整份招标文件所有正文都当成同权重风险来源
2. 资格性审查表、符合性审查表和采购需求正文可分权处理
3. 评分、技术、商务/验收主问题会更贴近真正应该修改的章节
4. 模板、附件、程序说明更不容易污染主问题和证据选择
5. 更符合“根据招标文件规则，抽取真正需要审查风险的内容”这一业务逻辑

## 风险与边界

### 风险一：过早排除 supporting_risk_scope

符合性审查表、投标人须知中有时也会埋实质性限制竞争条款。

因此第一版应：

- 先降权，不宜一刀切删除

### 风险二：结构块识别受 section_path 质量影响

如果 section_path 本身切分不稳，结构块分类也会受影响。

因此第一版要明确：

- 这是结构识别层
- 不是精确文档版式还原层

### 风险三：和 requirement_scope_layer 职责重叠

所以必须坚持：

- 业务结构层看“章节/区块角色”
- 条款语义层看“条款功能和效力”

## 当前结论

从整体架构看，当前不仅需要“条款语义分层层”，还需要再往上补一层：

- `tender_document_risk_scope_layer`

它的职责是：

- 先从招标文件业务结构上识别出真正承载采购需求风险的板块
- 再把这些板块里的 clause 送入 `requirement_scope_layer`

这样后续风险识别 engine 才能真正围绕：

- 资格
- 评分
- 技术
- 商务/验收
- 合同条款中与采购需求直接相关的部分

来工作，而不是继续把整份招标文件内容混成一锅。
