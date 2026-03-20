# 智能体孵化与蒸馏工厂设计

## 1. 目标

本方案定义一套统一的“强通用智能体辅助设计与校正、本地目标智能体稳定执行”的蒸馏式智能体生产方案。

目标不是一次性做出某一个智能体，而是沉淀一套后续可重复使用的方法层，让新智能体都能按统一流程快速生成、验证、增强和固化。

本方案也可简称为：

- **智能体孵化与蒸馏工厂**


## 2. 核心结论

新智能体的生产不再采用“需求来了就直接写代码”的方式，而采用以下标准闭环：

1. 业务需求定义
2. 样例驱动
3. 强通用智能体设计
4. 本地目标智能体生成
5. 对照验证
6. 持续蒸馏
7. 最终固化发布

其中：

- 强通用智能体负责：分析、设计、校正、差异归纳、增强建议
- 本地目标智能体负责：稳定执行、低成本运行、可审计输出、持续固化


## 3. 适用范围

本方法适用于本仓库后续所有新智能体，包括但不限于：

- 采购需求合规性检查智能体
- 政府采购预算需求智能体
- 后续的履约、比选、响应文件、规则编排等智能体


## 4. 分层角色

### 4.1 强通用智能体

角色：

- 需求分析者
- 主链设计者
- 差异诊断者
- 能力增强教练
- 蒸馏编排者

职责：

- 理解业务需求
- 设计目标智能体主链
- 设计 schema、规则、analyzer、评测方法
- 通过人工样例和目标智能体结果对照，发现缺口
- 指导目标智能体逐轮增强

### 4.2 本地目标智能体

角色：

- 稳定执行者
- 产品化输出者

职责：

- 固定输入输出
- 低成本、稳定运行
- 产出结构化结果
- 形成可复用、可发布、可审计的本地能力


## 5. 标准生命周期

### 阶段 A：业务需求定义

输入：

- 业务方目标
- 使用场景
- 用户角色
- 输入文档/数据
- 目标输出
- 约束条件

产物：

- 产品定位
- 范围边界
- 不做事项
- 第一版目标能力清单

### 阶段 B：样例资产准备

输入：

- 正样例
- 负样例
- 边界样例
- 历史人工处理结果

产物：

- benchmark 样本
- 样例标签
- 正负判断标准
- 评测覆盖说明

### 阶段 C：强通用智能体设计

输入：

- 业务定义
- 样例资产

产物：

- 主链方案
- 输入输出 schema
- 第一版 rules
- 第一版 analyzers
- 页面/导出/评测方案

### 阶段 D：本地目标智能体生成

输入：

- 设计蓝图

产物：

- 智能体目录骨架
- `schemas.py`
- `pipeline.py`
- `service.py`
- `rules/`
- `analyzers/`
- `product outline`

### 阶段 E：对照验证

执行三路或多路对照：

- 人工基准
- 强通用智能体判断
- 本地目标智能体判断

比较：

- 是否命中主问题
- 是否存在误报漏报
- 输出是否可用
- 哪一层导致偏差

建议统一记录为：

- `ValidationComparison`

### 阶段 F：持续蒸馏

把差异转成增强动作：

- 补结构层
- 补规则
- 补 analyzer
- 补仲裁
- 补导出
- 补 benchmark

建议统一记录为：

- `DistillationRecommendation`

### 阶段 G：固化发布

当目标智能体达到可用阈值后，固化：

- 规则集
- analyzer
- schema
- benchmark
- 导出格式
- 页面入口
- 运维方式


## 6. 与仓库四层架构的关系

本方案在仓库中的定位如下：

- `core/`
  - 共享底座
- `agents/`
  - 已成型产品化智能体
- `incubator/`
  - 智能体孵化与蒸馏工厂
- `apps/`
  - 应用入口层

也就是说：

- `incubator/` 不直接承担最终产品判断
- `incubator/` 负责定义“智能体是如何被生产出来的”


## 7. incubator 层建议结构

```text
src/agent_compliance/incubator/
  __init__.py
  lifecycle.py
  scaffold_generator.py
  factory.py
  blueprints/
    __init__.py
    registry.py
  scaffolds/
    __init__.py
  evals/
  improvement/
```

说明：

- `lifecycle.py`
  - 定义标准生命周期与阶段对象
  - 管理 `SampleSet / ValidationComparison / DistillationRecommendation / IncubationRun`
- `scaffold_generator.py`
  - 根据蓝图生成最小智能体骨架
- `factory.py`
  - 把蓝图、脚手架、生命周期和蒸馏报告串成统一启动入口
- `blueprints/`
  - 定义不同智能体类型的标准蓝图
  - 提供蓝图注册表与标准查询入口
- `scaffolds/`
  - 定义脚手架模板与生成入口
- `evals/`
  - 复用或扩展孵化评测能力
  - 统一输出蒸馏报告与对照复盘结果
- `improvement/`
  - 沉淀差异分析和增强候选


## 8. 蓝图类型建议

第一版建议至少定义两类蓝图：

### 8.1 审查型智能体蓝图

适用于：

- 合规性检查
- 风险审查
- 条款审查

典型结构：

- 输入文档
- 结构化解析
- 规则扫描
- analyzer
- 仲裁
- 法规依据


## 9. 标准蒸馏报告

为了避免每个智能体都各自发明“差异复盘”的格式，`incubator` 层应统一产出蒸馏报告。

第一版标准报告至少包含：

- 智能体标识与本轮孵化标题
- 生命周期完成度
- 样例集数量
- 对照记录数量
- 蒸馏建议数量
- 按优先级汇总的建议分布
- 按目标层汇总的建议分布
- 各阶段明细

建议由：

- `build_distillation_report()`
- `render_distillation_report_markdown()`

统一输出结构化结果和 Markdown 结果，后续再接到更完整的评测与自动留痕流程。


## 10. 最小工厂入口

为了避免“生命周期、蓝图、脚手架、报告”彼此分散，`incubator` 层应提供一个最小工厂入口：

- `bootstrap_agent_factory()`

第一版职责：

- 按 `agent_key` 取标准蓝图
- 生成最小智能体骨架
- 初始化一轮 `IncubationRun`
- 自动记录需求定义、设计和目标智能体生成阶段的初始产物
- 同时产出结构化蒸馏报告和 Markdown 报告

这样后续孵化一个新智能体，不再是手工拼装，而是按统一工厂入口启动。
- 导出

第一版对应实现：

- `src/agent_compliance/incubator/blueprints/review_agent.py`

### 8.2 预算分析型智能体蓝图

适用于：

- 预算需求分析
- 数量单价一致性
- 预算依据校验

典型结构：

- 输入预算材料
- 表格/条目解析
- 核算规则
- 预算 analyzer
- 差异与异常输出

第一版对应实现：

- `src/agent_compliance/incubator/blueprints/budget_agent.py`


## 9. 蓝图对象建议

蓝图不应只是说明文字，后续应作为脚手架生成器和生命周期编排的结构化输入。

第一版统一使用：

- `AgentBlueprint`

建议至少包含：

- `agent_key`
- `agent_name`
- `agent_type`
- `goal`
- `inputs`
- `outputs`
- `shared_capabilities`
- `required_files`
- `default_directories`
- `incubation_focus`

## 10. 生命周期记录对象建议

为了让孵化闭环能真正被执行和追溯，生命周期不应只停留在“阶段枚举”，而应进一步包含：

- `SampleSet`
  - 一组正样例、负样例、边界样例和 benchmark 引用
- `ValidationComparison`
  - 一次人工、强通用智能体、目标智能体的对照结果
- `DistillationRecommendation`
  - 一条针对结构层、规则、analyzer、仲裁或导出的增强建议
- `IncubationStageRecord`
  - 某个阶段的执行状态、输出、样例、对照和建议
- `IncubationRun`
  - 一次完整孵化/蒸馏 run 的统一记录对象

## 11. 脚手架生成建议

后续每个新智能体都应尽量通过脚手架起步，而不是手工散建。

第一版建议脚手架至少自动生成：

- `schemas.py`
- `pipeline.py`
- `service.py`
- `rules/__init__.py`
- `analyzers/__init__.py`
- `docs/product-specs/<agent>-product-outline.md`

## 12. 评测与蒸馏要求

每轮孵化都应保留：

- 输入样例
- 当前版本输出
- 人工基准
- 差异说明
- 增强结论
- 回归结果

避免“感觉更好了”的非可追溯增强。

## 13. 第一版落地范围

第一版不追求把工厂完全自动化，而是先完成以下最小闭环：

1. 定义生命周期对象
2. 建立 `blueprints/` 与 `scaffolds/` 目录
3. 落 `review_agent` 与 `budget_agent` 蓝图
4. 形成正式设计文档
5. 让新智能体（预算需求智能体）优先按这套方法孵化

## 14. 下一步建议

按优先级建议继续做：

1. 让 `budget_demand` 第一版严格按该流程起步
2. 补 `docs/product-specs` 级别的产品 outline 自动生成
3. 再把 scaffold 入口接到 CLI 或内部孵化命令
4. 把 `ValidationComparison` 和 `DistillationRecommendation` 接到统一评测报告
