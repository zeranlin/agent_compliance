# 政府采购预算需求智能体仓内架构方案

## 1. 目标

在不破坏当前“采购需求合规性检查智能体”独立能力的前提下，在同一仓库内孵化第二个独立智能体：

- **产品名**：政府采购预算需求智能体
- **核心目标**：围绕政府采购预算需求形成、预算测算、预算依据整理、预算约束校验和预算复核，输出结构化的预算需求分析结果

当前阶段优先回答两个问题：

1. 是否需要新开项目
2. 如果不新开项目，仓内应如何隔离与复用

结论是：

- **当前不建议立即新开项目**
- **建议在当前仓库内以“第二个独立智能体”方式孵化**
- **等预算需求智能体的业务边界、输入输出和复用边界稳定后，再评估是否拆仓**


## 2. 为什么当前不建议直接新开项目

### 2.1 高复用基础层已经存在

当前仓库已经具备以下可直接复用的基础能力：

- 文档解析与标准化
- 招标文件/采购文件结构化解析
- 品目识别与知识画像
- 本地法规依据层
- 缓存与复审一致性
- 导出能力
- Web 外壳、任务轮询、进度展示
- 本地大模型接入与混合审查模式

如果立即新开项目，会重复建设：

- 文档入口
- 结构化解析
- 引用资料层
- 导出与前端框架
- 评测与回归能力

### 2.2 当前最需要先验证的是业务边界，不是仓库边界

“预算需求智能体”现在更像：

- 一个新的业务域
- 一条新的审查/分析流水线
- 一个新的产品子入口

它还不一定需要独立仓库，但一定需要：

- 独立产品定位
- 独立主链
- 独立规则/分析器/输出 schema

### 2.3 先仓内孵化，更利于 A/B 比较和共享演进

仓内孵化的收益：

- 可以直接复用当前解析器和法规层
- 可以共享前端壳和任务机制
- 可以逐步验证预算链与合规链的边界
- 可以先做“共享底座 + 独立业务流水线”，后续再决定是否拆仓


## 3. 建议的总架构

建议把仓库从“单智能体 + 多模块”升级成：

- **共享基础平台层**
- **采购需求合规性检查智能体**
- **政府采购预算需求智能体**

### 3.1 逻辑分层

```text
原始文件/输入
-> 共享基础层
   -> normalize
   -> tender_document_parser
   -> catalog
   -> legal_authorities
   -> cache/export/web shell
-> agent router
   -> compliance review pipeline
   -> budget demand pipeline
-> agent-specific output
```

### 3.2 产品边界

#### 采购需求合规性检查智能体

关注：

- 资格
- 评分
- 技术
- 商务/验收
- 履约边界
- 发布前风险识别

#### 政府采购预算需求智能体

关注：

- 预算需求是否完整
- 预算测算依据是否充分
- 数量、单价、总价的口径是否一致
- 是否存在超范围预算、重复预算、漏项
- 是否存在预算依据缺失、预算结构失衡
- 是否满足内部预算编制与复核要求


## 4. 共享层与独立层边界

这是仓内孵化最关键的一部分。

### 4.1 建议共享的层

这些层建议继续作为共享基础平台保留，不要复制：

- `src/agent_compliance/parsers/`
  - 文档解析器
- `src/agent_compliance/pipelines/normalize.py`
  - 标准化输入
- `src/agent_compliance/pipelines/tender_document_parser.py`
  - 文件业务结构解析
- `src/agent_compliance/knowledge/`
  - 品目目录、法规依据、引用资料、知识画像
- `src/agent_compliance/cache/`
  - 缓存
- `src/agent_compliance/web/`
  - Web 壳、任务状态、导出接口
- `src/agent_compliance/pipelines/review_export.py`
  - 先保留为共享导出底座，后续可抽成更中性的 export 模块

### 4.2 必须独立的层

预算需求智能体应独立建设这些层：

- 独立 pipeline
- 独立 analyzers
- 独立 rules
- 独立 findings schema 扩展字段
- 独立页面入口
- 独立产品文档
- 独立 benchmark 与样本

也就是说：

- **共享“看懂文件”的能力**
- **独立“判断预算问题”的能力**

### 4.3 暂不共享的业务逻辑

以下内容当前不建议强行共用：

- 合规审查的资格/评分/技术/商务 analyzer
- 合规审查的风险等级体系
- 合规审查的主问题归并逻辑
- 合规审查的 review-check 页面结果组织方式

原因是：

- 预算需求智能体的主问题形态和当前合规审查会明显不同
- 如果强行复用，会让两个产品互相牵制


## 5. 仓内目录结构建议

第一版建议不要新建第二个顶级包，而是在当前包下增加独立子域。

### 5.1 推荐目录

```text
src/agent_compliance/
  budget/
    __init__.py
    schemas.py
    service.py
  pipelines/
    budget_review.py
    budget_export.py
    budget_stage_router.py
  analyzers/
    budget/
      __init__.py
      amount_consistency.py
      quantity_unit_price.py
      budget_basis_integrity.py
      duplicate_budget_item.py
      scope_boundary.py
  rules/
    budget_rules.py
  web/
    budget_views.py
docs/
  product-specs/
    budget-demand-agent-product-outline.md
  design-docs/
    budget-demand-agent-architecture.md
  evals/
    budget/
```

### 5.2 为什么这样切

这样切的好处是：

- 不打断当前 `review` 主链
- 预算链路可以独立演进
- 仍能复用共享基础层
- 未来若拆仓，迁移边界也比较清楚


## 6. 第一版模块边界

### 6.1 共享输入对象

预算需求智能体第一版继续复用：

- `NormalizedDocument`
- `StructuredTenderDocument`
- `Clause`

但预算智能体需要有自己的输出结构。

### 6.2 建议新增预算输出对象

第一版建议新增：

- `BudgetFinding`
- `BudgetReviewResult`

不要直接复用当前 `Finding` 和 `ReviewResult` 全部字段，因为预算问题和合规风险问题不完全相同。

预算问题更适合补这些字段：

- 预算项名称
- 数量
- 单位
- 单价
- 总价
- 预算依据来源
- 测算口径
- 差异类型
- 是否需财务/业务复核

### 6.3 第一版预算 pipeline 建议

建议主链：

```text
normalize
-> tender_document_parser (可选前置)
-> budget_stage_router
-> budget_rule_scan
-> budget_analyzers
-> budget_arbiter
-> budget_export
```


## 7. 部署建议

### 7.1 当前阶段部署建议

建议继续沿用当前仓库部署，不新拆服务：

- 同一个 Python 包
- 同一个 Web 服务
- 新增一个预算页面入口
- 新增 budget CLI 子命令

例如：

- `agent_compliance budget-review <file>`
- `/budget-check`

### 7.2 为什么先不拆成独立服务

因为当前阶段更重要的是：

- 验证预算智能体输入结构
- 验证问题类型和输出样式
- 验证与当前合规审查的共享层边界

而不是先上分布式部署。

### 7.3 未来拆仓/拆服务条件

满足以下条件时可考虑独立：

- 预算需求智能体已有稳定的产品定位
- 预算独立页面、导出、评测体系已经成熟
- 共享层与预算业务层边界已经清晰
- 两个智能体发布节奏明显不同


## 8. 第一版落地建议

第一版不要做太大，先做一个最小可运行链路。

### 第一版建议只覆盖这些预算问题

- 数量、单价、总价是否一致
- 预算项是否缺测算依据
- 是否出现重复预算项
- 是否存在明显超范围预算项
- 是否存在预算口径前后不一致

### 第一版建议只做这些产物

- 独立产品说明文档
- 独立 budget pipeline
- 独立 budget findings schema
- 独立 `/budget-check` 页面骨架
- 少量样本与 benchmark


## 9. 推荐实施顺序

### P0

1. 定 `BudgetFinding / BudgetReviewResult`
2. 新建 `budget_review.py`
3. 新建 `budget_rules.py`
4. 新建 `docs/product-specs/budget-demand-agent-product-outline.md`

### P1

5. 新建 `analyzers/budget/*`
6. 新建 `/budget-check`
7. 新建预算导出

### P2

8. 建立预算 benchmark
9. 建立预算差异学习闭环
10. 评估是否拆仓或拆服务


## 10. 结论

当前最合适的路径不是立即新开项目，而是：

- 在当前仓库内新增一个**独立的预算需求智能体子域**
- 共享文档解析、结构化解析、法规依据、缓存、导出和 Web 外壳
- 独立建设预算需求识别、预算问题判断、预算结果输出

一句话总结：

**当前阶段建议“同仓双智能体、共享底座、独立主链”，等预算需求智能体的业务边界稳定后，再决定是否拆成独立项目。**
