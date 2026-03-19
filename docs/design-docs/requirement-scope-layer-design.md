# 采购需求有效审查对象与条款语义分层设计

## 背景

当前代码审查已经补入了第一版 [effective-requirement-scope-filter-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/effective-requirement-scope-filter-design.md)，可以先把文档内容粗分为：

- 正文
- 模板
- 提示
- 格式

这已经能压住一部分“警示条款、格式说明、承诺模板污染主问题”的误报。

但在真实文件复跑中，仍暴露出一个更深层的结构问题：

- 即使内容来自正文，也不意味着它一定是“正式采购需求风险判断”的同等高权重输入
- 同一段正文可能分别承担：
  - 采购需求条款
  - 评分取证要求
  - 验收程序说明
  - 参考性说明
  - 配套义务
  - 模板残留
- 如果不继续做“条款功能”和“效力强度”分层，后续 `mixed_scope_boundary_engine`、`scoring_semantic_consistency_engine`、`commercial_lifecycle_analyzer` 和 `finding_arbiter` 仍会把不同性质的异常内容过宽合并

因此，当前需要把“正文过滤”升级成更完整的一层：

- `requirement_scope_layer`

它不只解决“是不是正文”，还要解决：

- 这段话是不是有效审查对象
- 这段话在文档里起什么作用
- 这段话对采购需求最终发布的约束强度有多高

## 目标

这层的目标不是新增更多风险规则，而是先把输入给下游引擎的“审查对象”整理干净。

具体目标：

1. 区分正式采购需求与非正式正文
2. 区分条款的业务功能
3. 区分条款对采购需求发布文本的约束强度
4. 在进入 `review.py + analyzers + finding_arbiter + evidence_selector` 前，给每段 clause 补上可计算的语义标签

## 非目标

第一版不做：

- 全量法律文书级文本分类
- 通用 NLP 段落语义理解平台
- 覆盖所有采购文件体裁
- 直接由这一层独立生成 findings

这层只服务一个核心目标：

- **提升采购需求风险识别的输入质量**

## 设计原则

### 1. 先分层，再判断风险

后续引擎应先知道：

- 这是什么内容
- 它起什么作用
- 它的效力有多强

再决定要不要作为高权重风险来源。

### 2. 正文不等于有效高权重审查对象

例如正文里的：

- 格式引导
- 附件说明
- 操作提示
- 参考性背景
- 宽泛兜底条款

不能与：

- 资格门槛
- 评分依据
- 技术参数
- 商务责任
- 验收程序

处于同等权重。

### 3. 功能识别优先于关键词命中

不能继续主要靠：

- “看见系统端口”
- “看见碳足迹”
- “看见保洁”

就直接推高到混合边界或模板错贴。

应该先识别它在条款里的功能：

- 是正式配套义务
- 还是模板残留
- 还是验收说明
- 还是格式要求

### 4. 这一层是通用输入层，不绑定某一个 analyzer

它服务：

- `scoring_semantic_consistency_engine`
- `mixed_scope_boundary_engine`
- `commercial_lifecycle_analyzer`
- `qualification_reasoning_engine`
- `finding_arbiter`
- `evidence_selector`

而不是为某一个场景单独写死。

## 新增的架构层

建议在当前主链中，把这层放在：

```text
normalize
-> requirement_scope_layer
-> stage / strategy / catalog
-> rule governance / rule scan
-> analyzers
-> llm nodes
-> finding_arbiter
-> legal / confidence / evidence
-> output
```

其中：

- `normalize` 负责把文件切成可处理的 `Clause`
- `requirement_scope_layer` 负责给每个 `Clause` 补语义分层
- 后续所有风险识别层都应消费这层结果

## requirement_scope_layer 的三部分

### 一、effective requirement scope

这是第一层，继续沿用并增强现有 `effective_requirement_scope_filter`。

输出字段建议：

- `scope_type`
  - `requirement_body`
  - `scoring_rule`
  - `technical_requirement`
  - `commercial_requirement`
  - `acceptance_requirement`
  - `template_text`
  - `prompt_text`
  - `format_text`
  - `background_text`
  - `attachment_sample`

作用：

- 先回答“这段话是什么类型的审查对象”

### 二、clause function classifier

这是第二层，识别条款功能。

输出字段建议：

- `clause_function`
  - `qualification_gate`
  - `scoring_factor`
  - `scoring_evidence`
  - `technical_parameter`
  - `proof_requirement`
  - `implementation_obligation`
  - `integration_obligation`
  - `commercial_term`
  - `acceptance_procedure`
  - `service_response_requirement`
  - `reference_note`
  - `template_residue_candidate`

作用：

- 先判断它是“资格门槛”“评分依据”“接口义务”“模板残留候选”还是“说明性内容”

### 三、effect strength classifier

这是第三层，识别条款对采购需求发布文本的约束强度。

输出字段建议：

- `effect_strength`
  - `strong_binding`
  - `medium_binding`
  - `weak_binding`
  - `reference_only`

示例理解：

- `必须/应当/不得/否则取消资格/必须提供报告`
  - 往往是 `strong_binding`
- `可结合实际/建议/优先/参考`
  - 往往是 `weak_binding` 或 `reference_only`

作用：

- 后续引擎可以决定：
  - 强约束条款高权重进入主问题判断
  - 弱约束或参考性说明只作为辅助上下文

## 需要给 Clause 增加的字段

建议在标准化后的 clause 对象上新增：

- `scope_type`
- `clause_function`
- `effect_strength`
- `is_effective_requirement`
- `is_high_weight_requirement`
- `scope_confidence`

建议含义：

- `is_effective_requirement`
  - 是否属于有效审查对象
- `is_high_weight_requirement`
  - 是否应高权重参与主问题生成

## 接入主链的位置

### 1. 接在 normalize 之后

`run_normalize()` 完成后，立即对所有 clauses 进行 `requirement_scope_layer` 标注。

这样后续：

- 规则扫描
- analyzer
- 大模型候选段选择
- 仲裁
- 证据选择

都能共享一份稳定的条款分层结果。

### 2. 在 review.py 中的使用

第一版建议接这些位置：

- `RuleHit -> Finding` 组装前
- 章节主题 finding 候选筛选前
- `mixed_scope_boundary_engine` clause 集合输入前
- `commercial_lifecycle_analyzer` clause 集合输入前
- `finding_arbiter` 最终收束前
- `review_evidence` 证据选择前

### 3. 在 llm 节点中的使用

第一版不强依赖，但建议作为输入压缩条件：

- `document_audit_llm` 优先看 `is_high_weight_requirement`
- `chapter_summary_llm` 优先看 `scope_type` 为评分/技术/商务要求的 clauses

## 第一版落地范围

第一版不要做太大，只覆盖当前最影响风险识别质量的场景。

### 范围一：条款类型四分法升级为八分法

先从现有：

- 正文 / 模板 / 提示 / 格式

升级为：

- `requirement_body`
- `scoring_rule`
- `technical_requirement`
- `commercial_requirement`
- `acceptance_requirement`
- `template_text`
- `prompt_text`
- `format_text`

### 范围二：补最关键的 clause_function

第一版只先做以下高价值功能类：

- `qualification_gate`
- `scoring_factor`
- `scoring_evidence`
- `technical_parameter`
- `integration_obligation`
- `commercial_term`
- `acceptance_procedure`
- `template_residue_candidate`

### 范围三：只做粗粒度 effect_strength

第一版只分：

- `strong_binding`
- `weak_binding`
- `reference_only`

先不追求更细。

### 范围四：优先接 4 个高价值 engine

第一版优先服务：

- `scoring_semantic_consistency_engine`
- `mixed_scope_boundary_engine`
- `commercial_lifecycle_analyzer`
- `finding_arbiter`

## 第一版预期收益

如果这一层落下去，预期直接改善的问题包括：

1. 混合边界问题不再过宽
2. 模板残留和正文越界义务不再轻易混并
3. 评分问题会更少被“说明性证据文字”污染
4. 商务链条问题会更少把宽泛说明和真正强约束条款合在一起
5. 证据摘录更容易选到真正应该改的正式条款

## 与现有模块的关系

### 与 effective_requirement_scope_filter 的关系

不是替代，而是升级。

可以理解为：

- `effective_requirement_scope_filter`
  - 是第一阶段的粗粒度版本
- `requirement_scope_layer`
  - 是下一阶段的完整分层版本

### 与 procurement_catalog_classifier 的关系

品目层回答：

- 这份文件买的是什么

条款语义分层回答：

- 这一段在文件里起什么作用

两层互补，不可互相替代。

### 与 finding_arbiter 的关系

仲裁层不应再自己承担过多“猜条款性质”的工作。

应改为：

- 优先消费 `requirement_scope_layer` 的标签
- 把仲裁重点放在：
  - 去重
  - 收束
  - 主问题优先级

## 第一版落地顺序

### Step 1

把 `effective_requirement_scope_filter.py` 升级成：

- `requirement_scope_layer.py`

或者在现有文件里扩展出：

- `scope_type`
- `clause_function`
- `effect_strength`

### Step 2

先在 `review.py` 接入：

- clause 预筛选
- mixed scope 输入筛选
- commercial analyzer 输入筛选

### Step 3

在 `review_arbiter.py` 里改成依赖：

- `is_high_weight_requirement`
- `template_residue_candidate`

### Step 4

在 `review_evidence.py` 中优先选：

- `strong_binding`
- `requirement_body / scoring_rule / technical_requirement / commercial_requirement`

## 风险与边界

### 风险一：误伤真正正文

如果分类过激，可能把真实风险条款错误降权。

因此第一版要保守：

- 先降权
- 少做直接删除

### 风险二：与现有 section_path 启发式冲突

条款功能识别不能完全依赖章节标题，也不能完全忽略章节标题。

第一版建议：

- 章节标题作为先验
- 正文句式和关键词作校正

### 风险三：再做成一个巨型 if/else 文件

因此第一版要明确：

- 这是“输入分层层”
- 不是所有 analyzer 的逻辑总汇

## 当前结论

从整体架构看，下一步不应继续按“物业/保洁残留”“接口义务外扩”“ESG/碳管理义务”这种单点修补推进。

更合理的方向是：

- 正式补齐 `requirement_scope_layer`

这层会把：

- 有效审查对象识别
- 条款功能识别
- 条款效力分层

作为统一输入层接入主链，让后续风险识别引擎在更干净、更稳定的语义对象上工作。

这会比继续补零散异常规则更接近人工审查的处理方式。
