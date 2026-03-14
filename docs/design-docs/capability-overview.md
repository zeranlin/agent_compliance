# 能力总览

## 目标定位

本项目当前不是单次问答式审稿助手，而是一个面向政府采购需求合规性审查的可持续进化型智能体工作框架。

它的目标不只是指出问题，而是逐步形成：
- 可审查
- 可引用
- 可定位
- 可改写
- 可积累
- 可更新
- 可复盘

的一整套能力体系。

## 一、审查能力

当前可以对以下对象进行结构化合规审查：
- 采购需求文本
- 招标文件、磋商文件、征集文件
- 资格条件
- 评分标准
- 技术/服务要求
- 合同条款
- 验收方案
- 框架协议项目的第二阶段成交规则

当前重点识别的高频风险包括：
- 资格条件与履约能力无直接关系
- 属地限制、本地备案、本地分支机构门槛
- 品牌、型号、平台、专有能力定向
- 同类业绩范围过宽、数量过高、定向设置
- 主观评分过重、分档不清、量化不足
- 奖项荣誉、信用等级、认证资质不当加分
- 资格条件或实质性要求被重复转化为评分优势
- 验收标准模糊、不可核验
- 付款前提不合理、责任边界失衡、绝对免责
- 框架协议项目中第二阶段成交规则不清晰

## 二、输出能力

当前可以按正式审查意见结构输出结果，至少包括：
- `条款位置`
- `原文摘录`
- `问题类型`
- `风险等级`
- `合规判断`
- `法律/政策依据`
- `适用逻辑`
- `修改建议`
- `建议替代表述`
- `是否需人工复核`

已建立正式模板：
- [正式审查意见模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/review-output-template.md)

## 三、精确定位能力

当前已经具备“主定位 + 辅助定位”的风险定位能力。

主定位字段包括：
- `document_name`
- `page_hint`
- `section_path`
- `clause_id`
- `table_or_item_label`
- `source_text`

辅助定位字段包括：
- `text_line_start`
- `text_line_end`

这意味着当前输出已经不仅能指出“有问题”，还能尽量帮助使用者快速回到原文件中的具体风险位置。

相关规范：
- [finding-schema.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/finding-schema.md)
- [location-field-spec.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/location-field-spec.md)

## 四、法规和案例引用能力

当前已经建立了本地可检索知识库，而不是每次临时查找引用。

已具备：
- [法规依据本地引用库](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/legal-authorities/README.md)
- [案例口径本地引用库](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/case-sources/README.md)
- [引用资料索引](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/reference-index.md)

引用资料已逐步具备统一元数据：
- `reference_id`
- `reference_type`
- `source_org`
- `source_url`
- `status`
- `review_topics`
- `related_rule_ids`
- `related_case_ids`
- `last_verified`

## 五、规则与案例映射能力

当前已经建立两类结构化资产：
- [法规依据库样表](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/legal-authority-library-starter.md)
- [典型案例库样表](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/case-library-starter.md)

并且已开始打通以下映射：
- `rule_id`
- `case_id`
- `reference_id`
- `source_url`
- `last_verified`

这意味着当前系统已经支持从问题类型反查规则、从规则反查引用资料、从案例反查支撑依据。

## 六、已沉淀的高频知识主题

当前本地知识库已经覆盖这些高频主题：
- 采购需求编制常见问题
- 同类项目业绩
- 主观评审客观化
- 综合评分法边界
- 属地限制与非歧视性审查
- 奖项荣誉与信用等级评分问题
- 资格条件与类似业绩设置
- 履约验收规范
- 合同付款前提与责任边界
- 框架协议项目规则
- 政府采购需求管理办法

## 七、持续进化能力

当前已经具备持续更新的结构基础：
- [法规依据体系](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/legal-authority-system.md)
- [案例库设计](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/case-library-design.md)
- [持续更新机制](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/continuous-update-mechanism.md)
- [更新自动化方案](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/update-automation-spec.md)

当前还具备标准化更新模板：
- [月度规则更新摘要模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/monthly-rule-update-template.md)
- [新增案例候选模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/new-case-candidates-template.md)
- [能力缺口评测报告模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/eval-gap-report-template.md)

## 八、工程化协作能力

当前在项目协作层面已形成以下工作方式：
- 每完成一个完整阶段结果后自动提交 Git
- 提交信息采用结论式表达
- 在明确要求时自动推送远端
- 每轮工作都尽量沉淀到仓库，而不是停留在对话中

## 九、当前能力边界

当前已经具备的能力：
- 能审查
- 能定位
- 能引用
- 能改写
- 能沉淀
- 能更新设计
- 能形成标准输出

当前尚未完全自动化的部分：
- 自动抓取官方站点并定期生成真实更新结果
- 自动将新增案例写入正式案例库
- 自动跑全量评测并输出真实差异报告

不过这些已经具备结构、模板、元数据、索引和本地知识库基础，离半自动或自动化落地已经较近。

## 维护约定

本文件应作为能力总览的长期维护文档。

后续如出现以下变化，应同步更新本文件：
- 新增重要审查能力
- 新增重要引用主题
- 新增定位字段或输出规范
- 新增更新机制或自动化能力
- 能力边界发生明显变化
