# 采购品目数据层

本目录用于存放代码审查主链路所使用的本地采购品目数据，包括：
- 运行时使用的最小可用品目知识映射
- 全量官方品目目录原始来源
- 后续结构化抽取产物

当前目标不是覆盖全国全量品目，而是先覆盖真实样本中最常见、最能提升审查准确性的高频场景。

当前数据文件：
- `catalogs.json`
- `raw/full-catalog-2022/source.pdf`
- `raw/full-catalog-2022/metadata.json`

设计来源：
- [procurement-catalog-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/procurement-catalog-layer-design.md)

使用原则：
- 先识别主品目，再识别次品目和混合采购边界
- 品目数据服务于规则路由、主题分析器优先级和标的域匹配
- 不把品目结果当成唯一真相，仍保留 `is_mixed_scope` 和 `confidence`

原始来源说明：
- `raw/full-catalog-2022/source.pdf` 为 2022 版《政府采购品目分类目录》原始快照
- 该原始文件将作为后续生成 `catalogs-full.json`、层级树和审查映射的权威来源
