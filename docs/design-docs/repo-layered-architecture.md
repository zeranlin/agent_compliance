# 仓库四层目录架构方案

## 1. 目标

为当前仓库建立一套清晰、可持续扩展的目录分层，支持：

- 在同一仓库内孵化多个政府采购智能体
- 共享通用底座，避免重复建设
- 保持每个智能体主链独立，避免业务逻辑混杂
- 沉淀“智能体标准生成与持续校正”的方法层

本方案确认仓库采用以下四层架构：

- **共享底座层 `core/`**
- **智能体产品层 `agents/`**
- **智能体孵化层 `incubator/`**
- **应用入口层 `apps/`**


## 2. 四层职责

### 2.1 `core/` 共享底座层

只放所有智能体都可复用的能力，不放具体产品判断。

建议逐步归入：

- 文档解析与标准化
- 招标文件/采购文件结构化解析
- 条款语义分层
- 品目目录、法规依据、知识画像
- 缓存
- 通用导出
- LLM 调用封装
- Web 公共能力
- 共享 schema

判断标准：

- 如果一个模块不关心“这是合规审查还是预算需求”，就应优先进入 `core/`


### 2.2 `agents/` 智能体产品层

每个智能体作为一条独立产品线存在：

- 自己的 schema
- 自己的 pipeline
- 自己的 service
- 自己的 rules
- 自己的 analyzers
- 自己的页面入口

当前建议至少包含两个子产品：

- `compliance_review/`
  - 采购需求合规性检查智能体
- `budget_demand/`
  - 政府采购预算需求智能体

判断标准：

- 如果一个模块已经明确属于某个智能体的独立业务判断，应归入对应 `agents/<agent_name>/`


### 2.3 `incubator/` 智能体孵化层

这层不直接承担最终用户能力，而是沉淀“新智能体如何从 0 到 1 生长出来”的方法。

建议后续容纳：

- 智能体蓝图
- 脚手架模板
- 孵化生命周期
- 评测模板
- 差异分析模板
- Scaffold 生成器

目标是把现在已经验证有效的路径沉淀下来：

1. 设计主链
2. 生成最小智能体骨架
3. 做人工对比
4. 持续调整规则、analyzer、仲裁
5. 回归验证
6. 固化成正式产品线


### 2.4 `apps/` 应用入口层

只负责把各智能体与共享能力挂到真正的运行入口上。

可逐步容纳：

- CLI 入口
- Web 聚合入口
- 智能体路由

判断标准：

- 如果某个模块主要负责“如何启动、如何路由、如何暴露服务”，就应优先进入 `apps/`


## 3. 推荐目录结构

```text
src/agent_compliance/
  core/
    __init__.py
  agents/
    __init__.py
    compliance_review/
      __init__.py
    budget_demand/
      __init__.py
  incubator/
    __init__.py
  apps/
    __init__.py
```

这次第一版只先创建四层包骨架，不在当前阶段强行搬迁现有代码。


## 4. 现有模块的未来归属原则

### 4.1 未来应逐步进入 `core/` 的模块

当前仓库中，这些模块长期看更适合进入共享底座层：

- `parsers/*`
- `pipelines/normalize.py`
- `pipelines/tender_document_parser.py`
- `pipelines/tender_document_risk_scope_layer.py`
- `pipelines/requirement_scope_layer.py`
- `knowledge/*`
- `cache/*`
- `models/llm_client.py`
- 通用导出底座
- Web 通用任务机制


### 4.2 未来应逐步进入 `agents/compliance_review/` 的模块

这些模块更像“采购需求合规性检查智能体”的专属产品逻辑：

- `pipelines/review.py`
- `pipelines/review_strategy.py`
- `pipelines/review_arbiter.py`
- `pipelines/review_evidence.py`
- `pipelines/review_export.py`
- `pipelines/confidence_calibrator.py`
- `pipelines/rewrite_generator.py`
- `analyzers/*`
- `rules/*`
- 采购人审查页、增强审查页、规则管理页中的合规审查专属逻辑


### 4.3 `agents/budget_demand/` 的第一版承载内容

预算智能体后续应优先在这里生长：

- `schemas.py`
- `pipeline.py`
- `service.py`
- `rules/`
- `analyzers/`
- `web/`

注意：

- 预算智能体不直接复用当前合规审查的 `Finding / ReviewResult`
- 它共享底座，但保持自己的业务输出对象


## 5. 迁移策略

### 第一阶段：先定架构，不搬旧代码

当前阶段只做：

- 新增正式目录架构文档
- 创建四层最小包骨架
- 预算智能体从新结构开始孵化

这样不会打断当前可运行能力。


### 第二阶段：新能力按新结构进入

从下一步开始：

- 预算智能体优先直接落到 `agents/budget_demand/`
- 新的共享模块优先进入 `core/`


### 第三阶段：逐步迁移现有合规审查产品

后续再分批把现有“采购需求合规性检查智能体”的专属逻辑迁到：

- `agents/compliance_review/`

共享能力则逐步迁到：

- `core/`

不建议一次性大迁移，避免影响当前稳定链路。


## 6. 与“智能体孵化层”的关系

四层架构里，`incubator/` 是未来很关键的一层。

它的意义在于：

- 新智能体不再靠临时堆代码生成
- 而是按统一蓝图、骨架、评测和调优闭环标准生成

也就是说：

- `core/` 解决“共享底座”
- `agents/` 解决“正式产品线”
- `incubator/` 解决“新智能体如何标准化诞生”
- `apps/` 解决“如何对外提供入口”


## 7. 结论

仓库正式采用以下四层目录架构：

- **共享底座层 `core`**
- **智能体产品层 `agents`**
- **智能体孵化层 `incubator`**
- **应用入口层 `apps`**

当前最稳妥的执行策略不是一次性迁移，而是：

1. 先确认四层目录方案
2. 先创建最小包骨架
3. 新能力优先按新结构落地
4. 再逐步把现有合规审查能力归位

一句话总结：

**同仓多智能体应采用“底座共享、产品独立、孵化可复用、入口统一”的四层目录架构。**
