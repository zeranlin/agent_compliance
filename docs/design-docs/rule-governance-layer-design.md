# 规则治理层设计方案

## 1. 目标

在已经引入采购品目层的前提下，为现有规则体系补一层治理能力，解决两个问题：

- 规则越积越多后，如何保持可维护
- 不同采购品目下，如何让规则优先级、启用顺序和噪声控制更稳

第一版不重写现有 `rules/*.py`，而是在它们之上增加：

- `rule_registry`
- `rule_priority_profile`
- `catalog_sensitive_rule_router`

## 2. 当前问题

当前规则层已经有：
- 规则定义
- 规则扫描
- 主题分析器和仲裁层

但仍缺：
- 规则家族和位阶
- 品目感知优先级
- 同一条款同一风险簇的规则冲突治理

这会导致：
- 命中噪声仍偏多
- 某些场景下相近规则重复命中
- 品目层虽然已接入主链路，但规则层还未被真正治理

## 3. 第一版方案

### 3.1 `rule_registry`

职责：
- 统一登记所有正式规则
- 为每条规则补治理元数据

当前字段：
- `rule_id`
- `issue_type`
- `rule_family`
- `source_section`
- `merge_key`
- `governance_tier`
- `default_priority`
- `related_reference_ids`

说明：
- 第一版直接从 `rules/*.py` 动态构建，不额外维护第二份规则正文

### 3.2 `rule_priority_profile`

职责：
- 定义默认规则家族优先级
- 定义按审查领域的加权策略

当前数据文件：
- `data/rule-governance/rule-priority-profile.json`

第一版支持：
- 默认家族优先级
- 按 `primary_domain_key` 的家族加权
- 按 `issue_type` 的加权
- 按 `rule_id` 的加权

### 3.3 `catalog_sensitive_rule_router`

职责：
- 根据主品目和审查领域，为规则生成运行时优先级
- 输出路由后的规则列表

第一版策略：
- 所有正式规则仍默认可参与扫描
- 但在同一条款、同一 `merge_key` 下，只保留当前品目场景优先级最高的规则

这样可以：
- 不破坏现有召回
- 先减少重复噪声
- 让品目层对规则扫描产生真实效果

## 4. 与现有主链路的关系

第一版接入点：

`procurement_catalog_classifier -> catalog_sensitive_rule_router -> run_rule_scan`

也就是：
- 先识别主品目
- 再对规则做场景优先级路由
- 最后规则扫描再生成命中

## 5. 第一版可见收益

- 信息化项目中，演示/评分/驻场类规则会更优先
- 家具项目中，样品/认证/售后类规则会更优先
- 物业项目中，商务和履约考核类规则会更优先
- 同一条款同一风险簇里，重复规则命中会减少

## 6. 后续演进方向

第二版继续补：
- 规则位阶
- 正式规则 / 候选规则 / 实验规则治理
- 按品目显式启停或降权
- 规则治理展示页
- 规则收益与副作用评估

## 7. 当前已落地的第二版增强

当前规则治理层已经继续前推到：

- `rule_registry` 开始具备状态分层
  - `formal_active`
  - `formal_catalog_sensitive`
  - `formal_support`
- `catalog_sensitive_rule_router` 开始支持：
  - 按品目显式停用规则
  - 按品目显式降权规则或问题类型
- `/rules` 页面开始展示：
  - 正式规则状态分层
  - 家族、位阶、默认启用状态

当前策略仍然保持保守：
- 只有已在样本中验证过的场景才做显式停用/降权
- 绝大多数规则仍默认启用
- 优先先解决同一品目下的明显噪声和模板污染
