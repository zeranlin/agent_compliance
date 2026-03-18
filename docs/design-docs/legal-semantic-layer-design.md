# 法规条文级语义层设计方案

## 1. 文档目标

本文档用于正式定义代码审查主链路中的第一层 `P0` 增强：

- `legal_clause_index`
- `legal_authority_reasoner`
- `issue_type_authority_map`

目标不是简单“多存几份法规”，而是把当前的法规引用层升级为：

- 可按条文定位
- 可按问题类型映射
- 可区分规则位阶
- 可解释适用逻辑
- 可在离线环境下稳定使用

## 2. 背景与问题

当前项目已经具备：
- 法规依据库
- 元数据规范
- 权威目录核验层
- 离线原文快照
- 标准化法规文本入口

但当前法规层主要还停留在：
- 摘要层
- 引用层
- 元数据层

它可以支撑“引用某部法规”，但还不够支撑：
- 具体是法规中的哪一条
- 为什么这个问题更适合引用这条，而不是那条
- 同一问题的主依据和辅依据如何排序
- 何时应该给出“需论证”，而不是直接定性为不合规

这意味着系统越来越会“发现问题”，但法规依据部分还没有完全升级成“可推理的条文级语义层”。

## 3. 总体目标

建立一条“问题类型 -> 条文依据 -> 位阶排序 -> 适用逻辑 -> 输出引用”的稳定链路。

目标主链路：

`issue_type / finding theme -> issue_type_authority_map -> legal_clause_index -> legal_authority_reasoner -> finding legal basis`

预期效果：
- 每类问题都有更稳定的优先依据
- 同一 `issue_type` 不再随机引用法规
- 输出中的依据更像人工审查意见
- 离线环境下仍可完成条文级引用

## 4. 设计原则

### 4.1 先支持高频问题，不追求一次覆盖全量法条

第一阶段先覆盖：
- 资格条件
- 评分标准
- 技术/服务要求
- 商务与验收
- 属地限制
- 奖项/认证/荣誉评分
- 主观评分
- 责任失衡

### 4.2 先支持条文级引用，再升级到条文级推理

第一阶段重点是：
- 法条可定位
- 条文可映射
- 位阶可排序

而不是一开始就追求复杂的法理推理。

### 4.3 离线优先

法规条文级语义层必须默认支持：
- 无网络环境可运行
- 本地快照可复用
- 权威元数据可追溯

### 4.4 主依据和辅依据分层输出

同一个问题可以有多个依据，但输出时必须明确：
- 主依据
- 辅依据
- 适用层级

避免“堆很多法规，但不解释为何引用”。

## 5. 三个核心模块

### 5.1 `legal_clause_index`

#### 职责

把离线法规原文快照和标准化文本，转换成可检索、可定位、可引用的条文索引。

#### 输入

- `data/legal-authorities/raw/*`
- `data/legal-authorities/normalized/*.txt`
- `docs/references/legal-authorities/*.md`

#### 输出

建议输出文件：
- `data/legal-authorities/index/clause-index.json`

每条建议字段：
- `clause_id`
- `reference_id`
- `doc_title`
- `doc_no`
- `authority_level`
- `validity_status`
- `chapter_label`
- `article_label`
- `clause_text`
- `keywords`
- `review_topics`
- `source_url`
- `canonical_registry_url`
- `last_verified`

#### 作用

- 支撑按条文检索
- 支撑按 `reference_id` 反查具体条文
- 支撑按 `issue_type` 匹配候选法条

---

### 5.2 `issue_type_authority_map`

#### 职责

定义“某类问题通常优先引用哪些法条和规则层级”。

#### 输入

- 高频 `issue_type`
- 高频章节主问题
- 法规依据库
- 条文索引

#### 输出

建议输出文件：
- `data/legal-authorities/index/issue-type-authority-map.json`

每类问题建议字段：
- `issue_type`
- `primary_reference_ids`
- `primary_clause_ids`
- `secondary_reference_ids`
- `secondary_clause_ids`
- `authority_priority`
- `reasoning_template`
- `fallback_review_topics`
- `requires_human_review_when`

#### 作用

- 给每类问题稳定的主依据
- 避免同类问题引用口径漂移
- 为 `legal_authority_reasoner` 提供推理起点

---

### 5.3 `legal_authority_reasoner`

#### 职责

把“finding / issue_type / 主问题”转成更像人工审查的法规依据输出。

#### 输入

- `Finding`
- `issue_type`
- `section_path`
- `risk_level`
- `issue_type_authority_map`
- `legal_clause_index`

#### 输出

建议结构：
- `primary_authority`
- `secondary_authorities`
- `authority_level`
- `legal_or_policy_basis`
- `applicability_logic`
- `reasoning_confidence`
- `needs_human_review`
- `human_review_reason`

#### 作用

- 给 finding 生成更稳定的法规依据
- 统一主依据和辅依据排序
- 支撑“需论证”与“直接不合规”的分流

## 6. 数据层设计

### 6.1 目录建议

```text
data/legal-authorities/
  raw/
  normalized/
  index/
    authorities.json
    clause-index.json
    issue-type-authority-map.json
```

### 6.2 与现有资料的关系

- `docs/references/legal-authorities/*.md`
  - 继续作为人读版摘要和元数据源
- `data/legal-authorities/raw/*`
  - 作为离线权威原文快照
- `data/legal-authorities/normalized/*.txt`
  - 作为标准化法规文本
- `index/*`
  - 作为运行时结构化知识层

## 7. 接入主链路的位置

建议接入点：

### 7.1 在 `review` 输出后处理阶段

在主题分析器和仲裁之后，为每条保留下来的主问题补法规依据。

目标链路：

`findings -> legal_authority_reasoner -> enriched_findings`

### 7.2 在 `difference_learning_loop` 中

如果某类问题长期无法稳定映射到主依据，应在差异学习中产出：
- 新条文索引建议
- 新 `issue_type_authority_map` 建议

### 7.3 在 `benchmark` 中

后续 benchmark 不只评估“问题有没有抓到”，还要评估：
- 主依据是否稳定
- 位阶是否正确
- 是否应为“需论证”

## 8. 与人工审查逼近的关系

法规条文级语义层会直接提升 4 个方面：

### 8.1 提升理由严谨性

从“引用某部法规”升级成“引用某条法条/某类条款”。

### 8.2 提升一致性

同样的问题，不会每轮引用不同依据。

### 8.3 提升改稿可用性

输出更像人工正式审查意见：
- 主依据
- 适用逻辑
- 位阶说明

### 8.4 提升离线能力

在没有网络的情况下，仍可做条文级引用和理由生成。

## 9. 分阶段落地建议

### P0-1：条文索引基础层

优先实现：
- `legal_clause_index`
- 先覆盖高频法规
- 先支持条文抽取和结构化索引

首批建议覆盖：
- 《政府采购法》
- 《政府采购法实施条例》
- 《政府采购需求管理办法》
- 《政府采购货物和服务招标投标管理办法》
- 《政府采购促进中小企业发展管理办法》

### P0-2：问题类型映射层

优先实现：
- `issue_type_authority_map`

先覆盖高频问题：
- `excessive_supplier_qualification`
- `geographic_restriction`
- `scoring_content_mismatch`
- `ambiguous_requirement`
- `one_sided_commercial_term`
- `unclear_acceptance_standard`
- `technical_justification_needed`

### P0-3：依据推理层

优先实现：
- `legal_authority_reasoner`

先做到：
- 主依据选择
- 辅依据补充
- 位阶和适用逻辑输出
- “需论证/待复核”分流

## 10. 第一版成功标准

第一版完成后，至少应满足：
- 高频 `issue_type` 有稳定主依据映射
- `review` 输出可自动补充条文级法规依据
- 离线环境可完成依据检索和引用
- 同类问题在多份文件中依据口径更稳定

## 11. 一句话结论

法规条文级语义层不是“再补几份法规摘要”，而是要把当前法规层从：

- 元数据和引用层

升级为：

- 条文索引层
- 问题映射层
- 依据推理层

也就是正式建立：
- `legal_clause_index`
- `issue_type_authority_map`
- `legal_authority_reasoner`

这会是当前代码审查从“会引用法规”走向“会按条文级语义稳定说明为什么”的关键第一步。
