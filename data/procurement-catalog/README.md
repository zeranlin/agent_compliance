# 采购品目数据层

本目录用于存放代码审查主链路所使用的本地采购品目数据，包括：
- 运行时使用的最小可用品目知识映射
- 全量官方品目目录原始来源
- 后续结构化抽取产物

当前目标不是覆盖全国全量品目，而是先覆盖真实样本中最常见、最能提升审查准确性的高频场景。

当前数据文件：
- `catalogs.json`
- `catalogs-full.json`
- `catalog-knowledge-profiles.json`
- `review-domain-map.json`
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

当前全量骨架说明：
- `catalogs-full.json` 已完成第一版全量骨架抽取
- 当前版本优先保证 `catalog_code / catalog_name / level / parent_code / category_type` 可用
- `description` 字段暂未做精细抽取，后续会在不破坏层级稳定性的前提下再补全文释义

当前审查映射说明：
- `review-domain-map.json` 已完成第一版审查领域映射
- 当前版本先把全量官方品目映射到高频审查领域：
  - 家具
  - 窗帘及被服
  - 物业管理服务
  - 信息化平台及系统运维
  - 医疗设备
  - 药品及医用配套
  - 标识标牌及宣传印制
  - 设备供货并安装调试
  - 餐饮托管及食堂运营
- 当前映射同时保留官方编码、编码前缀和关键词回退，以便后续分类器逐步从“最小品目集”升级到“全量官方目录 + 审查领域映射”的两层结构

当前品目知识画像说明：
- `catalog-knowledge-profiles.json` 已完成第一版
- 当前版本把高频场景的：
  - 常见合理要求
  - 高风险画像
  - 常见错位线索
  - 边界说明
  - 建议优先 analyzer
  抽成独立知识层
- 这层不负责“分类”，而是负责回答“这种品目通常怎么审、哪些问题最常见”
