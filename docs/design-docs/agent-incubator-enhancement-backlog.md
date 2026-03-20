# 智能体孵化与蒸馏工厂剩余增强项清单

## 1. 当前判断

`智能体孵化与蒸馏工厂` 当前已达到 **完整 MVP**，整体完成度大约为 **88%**。

剩余工作已不再是补主骨架，而是把工厂从“可运行的 MVP”继续推进到：

- 更自动
- 更稳定
- 更适合批量孵化新智能体
- 更容易证明目标智能体正在持续变强

本清单按优先级分为：

- `P0`：直接影响下一轮智能体孵化效率和闭环可信度
- `P1`：显著提升工厂的标准化、趋势化和复用能力
- `P2`：产品化和运营化增强项

---

## 2. P0 增强项

### 2.1 建议执行后自动触发回归

当前状态：
- 第一版已完成。
- 现在 `update-incubation-recommendation` 在更新建议状态时，已可直接接收回归样例三方文本并自动：
  - 生成新的 `ValidationComparison`
  - 追加到 `parity_validation`
  - 写回 `regression_result / capability_change`

目标：
- 不再只手工更新 `recommendation status`
- 当一条建议被标记为 `implemented` 或 `validated` 时，能自动关联一轮回归输入

当前缺口：
- 当前仍缺：
  - 自动触发标准回归任务，而不只是自动写回一轮 comparison
  - 将回归结果进一步自动沉入多轮趋势报告和建议收敛判断

建议落点：
- `src/agent_compliance/incubator/regression_runner.py`
- `src/agent_compliance/incubator/factory.py`
- `src/agent_compliance/apps/cli.py`

收益：
- 更快证明某条蒸馏建议是否真的让目标智能体变强
- 更少人工同步状态

### 2.2 ValidationComparison 自动采集二阶段

当前状态：
- 第一版已完成。
- 现在工厂已支持：
  - `--comparison-root <dir>` 从标准目录结构自动采集 comparison
  - 有 `SampleManifest` 时优先只采集 manifest 声明的样例

目标：
- 不只从三份标准文本构造 comparison
- 还能从标准目录、标准样例记录或现有 run 产物自动采集对照输入

当前缺口：
- 当前仍缺：
  - 从现有 run 产物自动反查 comparison 输入
  - 从样例资产 registry/版本目录直接采集 comparison
  - 对照采集质量校验与缺失项报告

建议落点：
- `src/agent_compliance/incubator/comparison_collector.py`
- `src/agent_compliance/incubator/comparison_builder.py`

收益：
- 降低人工准备 comparison 的门槛
- 提高不同智能体之间的对照一致性

### 2.3 run manifest 执行痕迹再细化

当前状态：
- 第一版已完成。
- 现在 `run manifest` 每个阶段已开始记录：
  - `events`
- 当前会自动落的事件包括：
  - 阶段状态更新
  - 阶段产物追加
  - 样例集追加
  - comparison 追加
  - 建议生成
  - 建议状态更新

目标：
- 让一轮 run 不只知道“阶段到了哪里”
- 还知道“什么时候加了样例、什么时候补了 comparison、什么时候更新了建议状态”

当前缺口：
- 当前仍缺：
  - 事件级唯一标识
  - 不同事件的责任来源标注（CLI/Web/自动联动）
  - 更细的事件筛选与趋势分析

建议落点：
- `src/agent_compliance/incubator/lifecycle.py`
- `src/agent_compliance/incubator/run_store.py`

收益：
- 方便复盘、续跑、回滚和多轮问题定位

---

## 3. P1 增强项

### 3.1 样例资产版本化

当前状态：
- 第一版已完成。
- 现在 `SampleManifest` 已开始支持：
  - `version`
  - `agent_key`
  - `benchmark_refs`
  - `change_summary`
- 工厂在接到样例清单时，也会同步落盘独立的版本化 `sample-manifest.json`

目标：
- 样例集从“登记清单”升级为“可版本追踪资产”

当前缺口：
- 当前仍缺：
  - 样例资产版本间差异对比
  - 样例资产与 run 的自动回挂关系
  - 样例版本与 benchmark 版本联动校验

建议落点：
- `src/agent_compliance/incubator/sample_registry.py`
- `docs/evals/incubator/`

收益：
- 便于长期积累样例资产
- 便于复现历史蒸馏结果

### 3.2 多轮趋势报告

当前状态：
- 第一版已完成。
- 现在 `compare-incubation-runs` 已开始输出：
  - `gap_series`
  - `recommendation_series`
  - `validated_change_series`
  - `gap_trend`
  - `validated_change_trend`
  - 高频目标层摘要

目标：
- 不只比较第 1 轮和第 2 轮
- 而是给出一条目标智能体的能力提升趋势

当前缺口：
- 当前仍缺：
  - 更长周期的 run 趋势图
  - 建议长期未落地项的单独摘要
  - 样例版本变化对趋势的影响解释

建议落点：
- `src/agent_compliance/incubator/evals/trend_reporter.py`

收益：
- 更容易判断某个目标智能体是否真正收敛
- 更适合做工厂周报/月报

### 3.3 蓝图模板分型增强

当前状态：
- 第一版已完成。
- 现在蓝图层已开始区分四类标准模板：
  - 审查型
  - 预算分析型
  - 调研生成型
  - 对比评估型
- 当前 `review_agent / budget_agent / demand_research_agent` 已从模板派生

目标：
- 当前蓝图从“按智能体”定义
- 继续升级到“按智能体类型”定义

建议先补的类型：
- 审查型
- 预算分析型
- 调研生成型
- 对比评估型

建议落点：
- `src/agent_compliance/incubator/blueprints/`

收益：
- 新智能体生成会更快
- 结构更可复用

### 3.4 scaffold 丰富化

目标：
- 当前脚手架能起最小骨架
- 已完成补齐：
  - 默认测试文件
  - 默认 product outline
  - 默认 eval skeleton
  - 当前落地文件：
    - `product_outline.md`
    - `evals/README.md`
    - `tests/test_agent_smoke.py`

建议落点：
- `src/agent_compliance/incubator/scaffolds/`
- `src/agent_compliance/incubator/scaffold_generator.py`

收益：
- 新智能体从 0 到可验证更快

---

## 4. P2 增强项

### 4.1 incubator Web 控制台二阶段

目标：
- 当前 `/incubator` 已能：
  - 启动首轮孵化
  - 查看 run
  - 补样例和对照后续跑
- 下一步可继续补：
  - 更新建议状态
  - 查看多轮 run 对比
  - 显示趋势摘要

收益：
- 更适合非 CLI 场景验证

### 4.2 产品化固化模板

目标：
- 当某个智能体达到可用阈值时，自动给出：
  - 发布 checklist
  - 运维口径
  - 交付模板
  - 验收模板

建议落点：
- `docs/product-specs/`
- `src/agent_compliance/incubator/productize.py`

### 4.3 工厂运营口径文档

目标：
- 给团队内部形成标准运营方式：
  - 什么叫一轮孵化完成
  - 什么叫一个目标智能体达到灰度验证
  - 什么叫达到可产品化发布

收益：
- 更适合团队协作和产品管理

---

## 5. 推荐实施顺序

### 第一阶段
优先做：
- `P0.1` 建议执行后自动触发回归
- `P0.2` ValidationComparison 自动采集二阶段
- `P0.3` run manifest 执行痕迹细化

目标：
- 让工厂真正从“有建议”变成“建议可自动验证”

### 第二阶段
优先做：
- `P1.1` 样例资产版本化
- `P1.2` 多轮趋势报告
- `P1.4` scaffold 丰富化

目标：
- 让工厂更适合稳定孵化第二个、第三个智能体

### 第三阶段
优先做：
- `P1.3` 蓝图模板分型增强
- `P2.1` incubator Web 控制台二阶段
- `P2.2` 产品化固化模板

目标：
- 让工厂更适合团队化使用和产品化交付

---

## 6. 一句话结论

当前 `智能体孵化与蒸馏工厂` 已达到完整 MVP，剩余约 `12%` 的增强项已经不是补主架构，而是继续提升：

- 自动回归
- 自动对照
- 多轮趋势
- 样例资产版本化
- 产品化固化

下一批最值钱的仍然是 `P0` 三项，因为它们最直接决定：
**工厂是否能更快、更稳地蒸馏出第二个、第三个本地目标智能体。**
