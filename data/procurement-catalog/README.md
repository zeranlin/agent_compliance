# 采购品目最小可用品目集

本目录用于存放代码审查主链路所使用的本地采购品目知识映射。

当前目标不是覆盖全国全量品目，而是先覆盖真实样本中最常见、最能提升审查准确性的高频场景。

当前数据文件：
- `catalogs.json`

设计来源：
- [procurement-catalog-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/procurement-catalog-layer-design.md)

使用原则：
- 先识别主品目，再识别次品目和混合采购边界
- 品目数据服务于规则路由、主题分析器优先级和标的域匹配
- 不把品目结果当成唯一真相，仍保留 `is_mixed_scope` 和 `confidence`
