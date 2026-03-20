# incubator 六层闭环映射

## 1. 目标

本文件把当前 `src/agent_compliance/incubator/` 已有模块，明确映射到“智能体孵化与蒸馏工厂”的六层闭环：

1. 业务需求定义
2. 样例驱动
3. 强通用智能体设计
4. 本地目标智能体生成
5. 对照验证
6. 持续蒸馏与固化发布

目的不是重复设计文档，而是回答两个问题：

- 当前 `incubator` 里每个文件到底属于哪一层
- 现在六层闭环是否已经各自有了明确实现落点


## 2. 一句话结论

当前 `incubator/` 已经不是“蓝图 + 脚手架”的平面工具目录，而是一个按六层闭环逐步落地的方法层与执行层组合体。

其中：

- `blueprints/` 更偏第 1、3 层
- `sample_registry.py` 更偏第 2 层
- `scaffold_generator.py / scaffolds/ / factory.py` 更偏第 4 层
- `comparison_builder.py / comparison_collector.py` 更偏第 5 层
- `distillation_engine.py / regression_runner.py / productize.py / evals/` 更偏第 6 层
- `lifecycle.py / run_store.py / __init__.py` 贯穿六层，是统一编排与状态底座


## 3. 六层映射总表

| 闭环层 | 目标 | 当前主要文件 | 当前作用 |
| --- | --- | --- | --- |
| 1. 业务需求定义 | 把业务需求转成目标智能体定义 | `blueprints/base.py` `blueprints/type_templates.py` `blueprints/*.py` `docs/product-specs/*-product-outline.md` | 定义智能体目标、输入、输出、模板类别和孵化重点 |
| 2. 样例驱动 | 把正负样例和 benchmark 资产标准化 | `sample_registry.py` `docs/evals/incubator/*.json` | 管理样例清单、版本、摘要和样例资产入口 |
| 3. 强通用智能体设计 | 把业务需求翻译成主链、schema 和增强重点 | `blueprints/*.py` `blueprints/registry.py` `agent-incubation-and-distillation-design.md` | 通过蓝图和模板定义目标智能体该怎么设计 |
| 4. 本地目标智能体生成 | 根据蓝图起出本地目标智能体骨架 | `scaffold_generator.py` `scaffolds/templates.py` `factory.py` | 生成 `schemas.py / pipeline.py / service.py / tests / evals / product_outline` |
| 5. 对照验证 | 把人工/强智能体/目标智能体的差异结构化 | `comparison_builder.py` `comparison_collector.py` `lifecycle.py` | 生成和收集 `ValidationComparison`，并写回 run |
| 6. 持续蒸馏与固化发布 | 把差异转成建议、验证建议、生成产品化模板 | `distillation_engine.py` `regression_runner.py` `productize.py` `evals/*` `report_writer.py` | 生成蒸馏建议、回归结论、趋势报告、产品化固化模板 |


## 4. 逐层展开

### 4.1 第一层：业务需求定义

**当前主要文件**

- `src/agent_compliance/incubator/blueprints/base.py`
- `src/agent_compliance/incubator/blueprints/type_templates.py`
- `src/agent_compliance/incubator/blueprints/review_agent.py`
- `src/agent_compliance/incubator/blueprints/budget_agent.py`
- `src/agent_compliance/incubator/blueprints/demand_research_agent.py`
- `src/agent_compliance/incubator/blueprints/special_checks_agent.py`
- `docs/product-specs/*.md`

**当前承担的职责**

- 定义 `AgentBlueprintTemplate`
- 定义 `AgentBlueprint`
- 给不同类型智能体建立标准模板
- 给具体智能体建立目标、输入、输出、孵化重点

**当前结论**

这一层已经具备：

- 类型模板
- 具体蓝图
- 业务目标文字化
- 产品初稿文档入口

也就是说，新智能体不再从空白需求直接开始，而是先被转成一份标准蓝图。


### 4.2 第二层：样例驱动

**当前主要文件**

- `src/agent_compliance/incubator/sample_registry.py`
- `docs/evals/incubator/*.json`

**当前承担的职责**

- 定义 `SampleAsset`
- 定义 `SampleManifest`
- 构造正样例 / 负样例 / 边界样例清单
- 记录版本、变更说明、benchmark 引用

**当前结论**

这一层已经不只是“把路径传给命令行”，而是开始把样例沉淀成版本化资产。


### 4.3 第三层：强通用智能体设计

**当前主要文件**

- `src/agent_compliance/incubator/blueprints/registry.py`
- `src/agent_compliance/incubator/blueprints/__init__.py`
- `docs/design-docs/agent-incubation-and-distillation-design.md`

**当前承担的职责**

- 管理蓝图注册表
- 提供 `list_blueprints()` / `get_blueprint()`
- 统一把“怎么设计目标智能体”沉成模板与蓝图

**当前结论**

这一层是整个工厂的“设计大脑”。

它不直接做目标智能体执行，但负责把：

- 业务需求
- 智能体类型
- 孵化重点

翻译成一个可以被脚手架和生命周期消费的标准对象。


### 4.4 第四层：本地目标智能体生成

**当前主要文件**

- `src/agent_compliance/incubator/scaffold_generator.py`
- `src/agent_compliance/incubator/scaffolds/templates.py`
- `src/agent_compliance/incubator/scaffolds/__init__.py`
- `src/agent_compliance/incubator/factory.py`

**当前承担的职责**

- 根据蓝图构造目录计划
- 渲染模板文件
- 生成最小目标智能体骨架
- 串起首轮工厂启动

**当前结论**

这一层已经能稳定生成：

- `schemas.py`
- `pipeline.py`
- `service.py`
- `rules/__init__.py`
- `analyzers/__init__.py`
- `web/__init__.py`
- `product_outline.md`
- `evals/README.md`
- `tests/test_agent_smoke.py`

这意味着工厂已经具备“生产本地目标智能体骨架”的最小能力。


### 4.5 第五层：对照验证

**当前主要文件**

- `src/agent_compliance/incubator/comparison_builder.py`
- `src/agent_compliance/incubator/comparison_collector.py`
- `src/agent_compliance/incubator/lifecycle.py`

**当前承担的职责**

- 根据三份标准文本构造 `ValidationComparison`
- 从标准目录采集 comparison
- 把对照结果写回 `IncubationRun`

**当前结论**

这一层已经具备：

- 手工 comparisons JSON 输入
- 三份文本自动生成对照
- 标准目录自动采集对照
- Web/CLI 续跑接入对照

也就是说，工厂已经能开始标准化记录“人工 vs 强智能体 vs 目标智能体”的差异。


### 4.6 第六层：持续蒸馏与固化发布

**当前主要文件**

- `src/agent_compliance/incubator/distillation_engine.py`
- `src/agent_compliance/incubator/regression_runner.py`
- `src/agent_compliance/incubator/productize.py`
- `src/agent_compliance/incubator/report_writer.py`
- `src/agent_compliance/incubator/evals/distillation_reporter.py`
- `src/agent_compliance/incubator/evals/run_comparison_reporter.py`

**当前承担的职责**

- 把 gap 转成 `DistillationRecommendation`
- 生成回归反馈
- 输出蒸馏报告
- 输出多轮趋势报告
- 输出产品化固化模板

**当前结论**

这一层已经同时覆盖：

- 发现差距
- 生成建议
- 回挂建议状态
- 回挂回归结果和能力变化
- 比较多轮趋势
- 生成产品化模板

也就是说，它已经不是“提出建议”为止，而是开始进入“建议是否真的变成能力”的闭环。


## 5. 贯穿六层的统一底座

### 5.1 `lifecycle.py`

这是六层闭环的统一状态模型。

当前核心对象包括：

- `IncubationStage`
- `IncubationStageRecord`
- `IncubationRun`
- `SampleSet`
- `ValidationComparison`
- `DistillationRecommendation`
- `IncubationEvent`

它的作用是：

- 把六层闭环收进同一条 run
- 让阶段状态、样例、对照、建议、事件都能统一追踪


### 5.2 `run_store.py`

这是六层闭环的统一落盘层。

当前负责：

- run manifest 序列化
- run manifest 写入
- run manifest 读取

也就是把“工厂执行过程”从内存对象变成可恢复、可比较、可留痕的产物。


### 5.3 `__init__.py`

这是六层闭环的统一导出入口。

当前已经把：

- 蓝图
- 生命周期对象
- 对照生成
- 蒸馏建议
- 工厂启动
- 报告写入
- 产品化模板

统一暴露出来，方便 CLI、Web 和后续其他层复用。


## 6. 当前目录和六层并不是一一对应

需要特别说明：

- 当前 `incubator/` 目录**不是**按六层物理拆目录
- 而是按“方法对象 + 执行对象 + 评测对象”组织

这是刻意的。

原因是：

- `lifecycle.py` 同时服务第 2、5、6 层
- `factory.py` 同时横跨第 3、4、5 层
- `productize.py` 属于第 6 层，但依赖第 5 层和 run 总结

所以当前更合理的是：

- **先用映射表保证逻辑清晰**
- **不急着把目录强拆成六个物理子目录**

后续如果 `incubator/` 再继续增长，再评估是否做物理分层。


## 7. 当前是否还需要继续分层

当前结论是：

- 方法论层面：已经按六层闭环成立
- 文件落点层面：已经能清楚映射到六层
- 目录物理层面：暂时不必继续强拆

更值钱的不是现在继续搬目录，而是继续让每一层：

- 更自动化
- 更标准化
- 更可恢复
- 更可评测


## 8. 一句话结论

当前 `incubator/` 应继续被理解为：

**按六层闭环组织的方法与执行工厂**

而不是：

**一个只负责脚手架生成的工具目录**

如果以后继续扩张，优先应该增加的是：

- 层与层之间的自动连接能力
- 而不是先做目录层面的过度物理拆分
