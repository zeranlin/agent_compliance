# 智能体孵化与蒸馏工厂设计

## 1. 目标

本方案定义一套统一的“强通用智能体辅助设计与校正、本地目标智能体稳定执行”的蒸馏式智能体生产方案。

目标不是一次性做出某一个智能体，而是沉淀一套后续可重复使用的方法层，让新智能体都能按统一流程快速生成、验证、增强和固化。

本方案也可简称为：

- **智能体孵化与蒸馏工厂**

配套映射文档：

- [incubator 六层闭环映射](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/incubator-six-layer-mapping.md)


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
- 政府采购需求调查智能体
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

当前已落第一版“需求定义层”页面能力：
- Web 页面：`/incubator/definition`
- 面向业务方辅助澄清：
  - 智能体名称
  - 业务需求
  - 使用场景
  - 用户角色
  - 输入项
  - 目标输出
  - 成功标准
  - 不做事项
  - 约束条件
- 当前会自动生成并落盘：
  - `*-requirement-definition.json`
  - `*-requirement-definition.md`
- 产物目录：
  - `docs/generated/incubator-definition/`

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

当前已落第一版产品化固化模板能力：
- 可通过 `productize-incubation-run <run_manifest>` 从单轮 run 自动生成：
  - `*-productization.json`
  - `*-productization.md`
- 当前模板至少包含：
  - `readiness_level`
  - 发布 checklist
  - 运维口径
  - 交付模板
  - 验收模板
- 生成后会自动把 run 的 `productization` 阶段标记为 `completed`


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
- `sample_registry.py`
  - 管理正样例 / 负样例 / 边界样例的登记与摘要
- `scaffold_generator.py`
  - 根据蓝图生成最小智能体骨架
  - 当前默认已补齐 `product_outline.md`、`evals/README.md`、`tests/test_agent_smoke.py`
- `factory.py`
  - 把蓝图、脚手架、生命周期和蒸馏报告串成统一启动入口
- `report_writer.py`
  - 把蒸馏报告落成标准 JSON 和 Markdown 产物
- `productize.py`
  - 把单轮 run 继续固化成产品化模板
  - 输出发布 checklist、运维口径、交付模板和验收模板
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


## 14. 内部命令入口

为了让工厂主线不仅可由 Python 调用，也可以由仓库内部统一触发，第一版应提供内部命令入口：

- `agent_compliance incubate-agent <agent_key>`

第一版支持：

- 指定蓝图
- 指定 agents 目标目录
- 指定蒸馏报告输出目录
- 注入正样例 / 负样例 / 边界样例
- 注入对照 JSON
- 自动落盘标准蒸馏报告

这样 `incubator` 才真正具备从命令行启动一轮标准孵化的能力。


## 15. 运行状态与恢复执行

为了让孵化过程支持中断恢复、多轮比较和标准留痕，`incubator` 层应把 `IncubationRun` 落成标准 run manifest。

第一版建议通过：

- `serialize_incubation_run()`
- `write_incubation_run()`
- `load_incubation_run()`

统一输出：

- `*-run.json`

这样每一轮孵化都会同时留下：

- 运行记录
- 蒸馏报告
- 标准骨架

后续再继续往“恢复执行”和“多轮对比”推进。

第一版恢复执行建议通过：

- `resume_agent_factory()`
- `agent_compliance incubate-agent --resume-run <run.json>`

让后续补充样例、对照结果和蒸馏建议时，可以继续并回原 run，而不是每次都从零开始。


## 11. 样例资产登记

为了把“样例驱动”做成标准能力，`incubator` 层应统一管理：

- 正样例
- 负样例
- 边界样例

第一版建议通过：

- `SampleAsset`
- `SampleManifest`
- `build_sample_manifest()`
- `summarize_sample_manifest()`

实现样例资产登记与摘要输出，再把结果转给生命周期中的 `SampleSet` 使用。


## 12. 差异到蒸馏建议的转换

为了让“对照验证 -> 持续蒸馏”真正闭环，`incubator` 层应提供最小的差异归纳引擎。

第一版建议通过：

- `summarize_validation_gaps()`
- `build_distillation_recommendations()`

把 `ValidationComparison` 中的差异点先统一汇总，再生成第一版蒸馏建议。

第一版目标不是替代强通用智能体设计，而是先把高频差异稳定映射到：

- 评分语义引擎
- 混合边界引擎
- 商务链路引擎
- 仲裁归并层
- 通用 review 主链


## 13. 标准产物落盘

为了让孵化过程可复盘、可追溯、可中断恢复，`incubator` 层应把蒸馏报告落成标准产物。

第一版建议通过：

- `write_distillation_report()`

统一输出：

- `*-distillation-report.json`
- `*-distillation-report.md`

这样后续每一轮孵化与蒸馏，都能留下结构化痕迹和人类可读报告。
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
- `product_outline.md`
- `evals/README.md`
- `tests/test_agent_smoke.py`

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
3. 落 `review_agent`、`budget_agent` 与 `demand_research_agent` 蓝图
4. 形成正式设计文档
5. 让新智能体优先按这套方法孵化
6. 提供 `incubate-agent` 统一命令入口
7. 落盘标准蒸馏报告与 run manifest

当前已完成第一轮真实 MVP 验证：

- 目标智能体：`政府采购需求调查智能体`
- 启动方式：`PYTHONPATH=src python3 -m agent_compliance incubate-agent demand_research ...`
- 标准产物：
  - `docs/generated/incubator/demand_research/*-distillation-report.md`
  - `docs/generated/incubator/demand_research/*-distillation-report.json`
  - `docs/generated/incubator/demand_research/*-run.json`
- 当前验证结论：
  - 已能按蓝图生成最小骨架
  - 已能登记样例清单和对照结果
  - 已能产出首轮蒸馏建议
  - 已能写出标准报告与恢复执行所需 manifest

当前也已开始补齐“自动对照生成”最小能力：

- 可由三份标准文本自动生成一条 `ValidationComparison`
- 输入对象：
  - `human_baseline`
  - `strong_agent_result`
  - `target_agent_result`
- 当前接入方式：
  - `incubate-agent --human-baseline-file --strong-agent-result-file --target-agent-result-file`
- 当前目标：
  - 先替代手工书写最基础的 `comparisons.json`
  - 让工厂更快进入“样例 -> 对照 -> 蒸馏建议”闭环

当前进一步补入了 `P0.2` 的第一版自动采集：

- 现已支持从标准目录结构自动采集多条 `ValidationComparison`
- 目录约定：
  - `<comparison_root>/<sample_id>/human_baseline.txt`
  - `<comparison_root>/<sample_id>/strong_agent_result.txt`
  - `<comparison_root>/<sample_id>/target_agent_result.txt`
  - `<comparison_root>/<sample_id>/summary.txt`（可选）
- 当前接入方式：
  - `incubate-agent --comparison-root <dir>`
  - `update-incubation-recommendation --comparison-root <dir> --sample-id <id>`
- 当前能力：
  - 若已提供 `SampleManifest`，则优先只采集 manifest 中声明的 `sample_id`
  - 若未提供样例清单，则按标准目录自动发现样例
- 当前目标：
  - 把自动对照从“三份文本直接输入”推进到“标准目录与样例资产可复用”
  - 为后续样例资产版本化和自动对照采集层继续铺路

当前也已开始补齐 `P0.3` 的第一版执行痕迹：

- `run manifest` 的每个阶段现在会继续记录 `events`
- 当前会自动记录的动作包括：
  - `set_stage_status`
  - `add_stage_output`
  - `add_sample_set`
  - `add_comparison`
  - `add_recommendation`
  - `update_recommendation_status`
- 蒸馏报告也已开始展示：
  - 总执行事件数量
  - 每个阶段最近的执行痕迹
- 当前目标：
  - 让一轮 run 不只知道“阶段到了哪里”
  - 还知道“什么时候补了样例、什么时候加了 comparison、什么时候更新了建议状态”

当前也已开始补齐 `P1.1` 的第一版样例资产版本化：

- `SampleManifest` 现在已开始携带：
  - `version`
  - `agent_key`
  - `benchmark_refs`
  - `change_summary`
- 当前接入方式：
  - `incubate-agent --sample-manifest-version <vN> --sample-change-summary <text>`
  - `incubate-agent --sample-manifest-file <manifest.json>`
- 当前产物：
  - 一旦本轮孵化传入样例清单，工厂会同步落盘独立的 `sample-manifest.json`
- 当前目标：
  - 让样例资产从“登记清单”升级成“可版本追踪、可回读、可复用的标准资产”

当前也已开始补齐 `P1.2` 的第一版多轮趋势报告：

- 现有 `compare-incubation-runs` 已从“最小 run 比较”升级成：
  - gap 序列
  - 蒸馏建议序列
  - 已记录回归/能力变化序列
  - gap 趋势判断
  - 能力增强走势判断
  - 高频目标层摘要
- 当前目标：
  - 不只知道两轮 run 差了什么
  - 还要看出同一目标智能体在多轮孵化中的“成长曲线”

当前也已开始补齐 `P1.3` 的第一版蓝图模板分型：

- 现有蓝图层已不再只按具体智能体定义
- 现在新增了四类标准模板：
  - 审查型
  - 预算分析型
  - 调研生成型
  - 对比评估型
- 当前具体蓝图：
  - `review_agent`
  - `budget_agent`
  - `demand_research_agent`
  已开始从对应模板派生
- 当前目标：
  - 让后续新智能体先选“类型模板”，再落具体蓝图
  - 减少每次重复定义 shared capabilities、目录结构和孵化重点

当前也已开始补齐“多轮蒸馏比较”最小能力：

- 可输入两轮或多轮 `run.json`
- 输出统一的多轮孵化比较报告
- 当前比较维度：
  - `gap_count`
  - `recommendation_count`
  - `completed_stages`
  - 重复出现的 `gap_points`
  - 重复成为增强重点的 `target_layer`
- 当前接入方式：
  - `compare-incubation-runs <run1> <run2> ...`

当前也已开始补齐“蒸馏建议执行状态跟踪”最小能力：

- 每条 `DistillationRecommendation` 现在具备：
  - `recommendation_key`
  - `status`
  - `resolution_notes`
- 当前支持的状态：
  - `proposed`
  - `accepted`
  - `implemented`
  - `validated`
  - `dropped`
- 当前接入方式：
  - `update-incubation-recommendation <run.json> <recommendation_key> --status ...`
- 当前目标：
  - 让工厂不只会“提出建议”
  - 还能记录建议是否真的进入实现、验证或被放弃

当前也已开始补齐“建议执行 -> 回归结果 -> 能力变化”最小回挂能力：

- 每条建议现在还可继续记录：
  - `regression_result`
  - `capability_change`
- 当前接入方式：
  - `update-incubation-recommendation ... --regression-result ... --capability-change ...`
- 当前目标：
  - 让工厂开始回答“哪条建议真的让目标智能体变强”
  - 让多轮 run 对比不只看 gap 数量，也能看能力变化记录

当前进一步补入了 `P0.1` 的第一版自动联动：

- `update-incubation-recommendation` 现在支持在更新建议状态时直接补：
  - `--sample-id`
  - `--human-baseline-file`
  - `--strong-agent-result-file`
  - `--target-agent-result-file`
  - `--comparison-summary`
- 当提供上述输入时，工厂会自动：
  - 构造新的 `ValidationComparison`
  - 追加到 `parity_validation`
  - 基于上一轮同样例对照自动生成：
    - `regression_result`
    - `capability_change`
- 这意味着“建议执行 -> 回归输入 -> 能力变化回挂”已经开始形成最小自动闭环，而不再完全依赖手工填写结论文本。

## 14. 下一步建议

按优先级建议继续做：

1. 让 `ValidationComparison` 支持更标准的自动生成入口
2. 补多轮 run 对比，明确“蒸馏后能力是否增强”
3. 记录 `DistillationRecommendation` 的执行状态与采纳结果
4. 再让新的目标智能体严格按该流程孵化
