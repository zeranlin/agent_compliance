# 能力总览

## 目标定位

本项目当前不是单次问答式审稿助手，而是一个面向政府采购需求合规性审查的可持续进化型智能体工作框架。

统一口径：
- 对外描述时，应同时承认两层含义：
- 一层是“体系化能力框架”，即本项目被设计成具备审查、定位、引用、改写、一致性复审、缓存复用和持续更新能力的政府采购合规审查智能体。
- 一层是“当前已验证交付能力”，即已经能够对真实采购文件执行正文提取、条款切分、结构化审查、正式意见输出、结果落库、Git 留痕与复审复用的完整闭环。

因此，本项目当前已经不是“帮你看一段采购需求有没有问题”的单点能力，而是一套面向政府采购需求合规性审查的可持续、可复核、可复用的审查体系。

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
- 人员画像限制，如性别、年龄、身高、外貌、特定履历
- 验收标准模糊、不可核验
- 付款前提不合理、责任边界失衡、绝对免责
- 框架协议项目中第二阶段成交规则不清晰

当前已经实际验证过的执行链路包括：
- 提取 `docx`、`pdf` 或稳定文本副本中的正文内容
- 对章节、表格、评分项和商务条款做定位化切分
- 输出正式审查意见和结构化 findings
- 将结果沉淀到仓库中的 `docs/generated/`
- 在完整阶段结果完成后自动提交并推送 Git

## 二、输出能力

当前可以按正式审查意见结构输出结果，至少包括：
- `问题标题`
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
- [业务方/采购人修改用正式审查意见表模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/business-facing-review-table-template.md)

当前还具备一类更偏落地修改的交付能力：
- 可输出“复审结果可直接给业务方/采购人修改”的正式审查意见表
- 强调风险位置、原文摘录、修改建议和建议替代表述并列展示
- 适合业务、采购、法务、代理机构协同改稿
- 当用户指定正式审查格式时，可严格按照固定字段顺序输出：
  - `主要问题`
  - `位置`
  - `页码提示`
  - `条款编号`
  - `辅助行号`
  - `原文摘录`
  - `风险类型`
  - `风险等级`
  - `合规判断`
  - `依据`
  - `适用逻辑`
  - `修改建议`
  - `建议替代表述`
- 上述固定标题式输出已作为标准能力要求，适用于正式复审、复核意见、业务改稿和采购人沟通场景

当前也支持一类机器可复用交付：
- 产出符合 [finding-schema.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/finding-schema.md) 的结构化 JSON 结果
- 支持后续复审直接复用 findings 缓存，而不是重复全量自由推理
- 对已聚合的相邻命中，生成更接近正式审查意见写法的问题标题和统一改写建议

## 三、文档标准化与切分能力

当前能力不只是“读原文后直接判断”，而是已经具备将原始采购文件转化为稳定中间表示的能力方向。

当前已验证或已明确设计的能力包括：
- 从 `docx`、`pdf` 或稳定文本副本中提取正文
- 对原文做章节、条款、表格项、评分项和商务条款切分
- 在离线执行引擎中输出层级化 `section_path`、`source_section` 和 `table_or_item_label`
- 为后续审查保留稳定文本副本，便于复核和复用
- 为后续缓存复用预留标准化字段，如 `file_hash`、`normalized_text`、`section_map`、`clause_map`、`page_map`、`line_map`

这意味着当前体系的目标不是每次都从零自由阅读整份文件，而是尽量把文件先转成可复用、可比对、可续跑的标准输入。

相关设计：
- [consistency-and-caching-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/consistency-and-caching-design.md)

## 四、精确定位能力

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

当前离线执行引擎已能在无网络情况下把常见章节标题、评分表标签和条款片段映射到 `section_path`、`source_section`、`table_or_item_label`，并基于本地 `page_map` 为 finding 回填 `page_hint`。复杂评分表中已可区分“评分因素、技术部分、价格”等语义标签与“序号、内容、权重(%)、评分准则”等普通列头，以减少定位噪声。当原文缺少显式分页标记时，当前会回退为估算页号，后续仍需继续补强精确页映射。

该能力已适用于：
- Word
- PDF
- 表格类采购文件
- 评分表
- 合同模板

相关规范：
- [finding-schema.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/finding-schema.md)
- [location-field-spec.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/location-field-spec.md)

## 五、法规和案例引用能力

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

当前还具备法规依据分层使用能力：
- 先引用法律和实施条例等高位阶规则
- 再补充财政部规章和管理办法
- 再参考政策解读、官方答复、地方细则和典型案例
- 对法域差异明显、规则有效性待核实的问题，升级为人工复核而不是强行下结论

相关设计：
- [legal-authority-system.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/legal-authority-system.md)

## 六、规则与案例映射能力

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

## 七、规则命中与增量复审能力

当前系统已明确采用“规则初筛 + 边界判断 + 结果固化”的能力方向，而不是每轮都做整篇自由推理。

当前已具备或已明确设计的能力包括：
- 对高频风险主题建立规则命中思路，如品牌指定、属地限制、奖项荣誉加分、主观评分、责任失衡等
- 将规则命中结果作为大模型进一步判断的前置输入
- 对同一定位区段、同类问题、相邻行的规则命中做本地聚合，减少重复 findings
- 在显式开启缓存且文件哈希、规则版本和引用快照未变化时，直接复用已缓存的 review 结果
- 在仅输出格式变化时，直接复用 findings 重排结果
- 在仅引用资料变化时，只重算受影响 finding
- 在仅文件局部变化时，只对受影响条款重新切分、重新命中规则、重新判断
- 对投标文件格式附件中的重复技术参数 finding 做后处理去重，避免与正文重复报警
- 对过长原文生成代表性摘录，并对跨章节重复出现的同类技术参数做归并输出

这意味着后续复审默认优先复用：
- 标准化输入
- 规则命中缓存
- findings 缓存

相关设计：
- [consistency-and-caching-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/consistency-and-caching-design.md)

## 八、已沉淀的高频知识主题

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

## 九、案例学习与知识积累能力

当前能力不只依赖法规条文，还强调从案例、失败样本和优秀改写中持续学习。

当前已具备或已明确设计的能力包括：
- 建立典型案例库而不是只保留零散链接
- 收集并结构化高风险案例、中风险边界案例、低风险优化案例和明显合规反例
- 保存“风险条款 -> 合规替代表述”的优秀改写样本
- 保存误报、漏报和历史失败样本，作为后续纠偏依据
- 将高价值案例进一步转成 benchmark 测试题
- 每次新增重要案例时补充对应的审查启发规则

这意味着系统目标不仅是“做完这次审查”，还包括“把这次经验变成下次能力”。

相关设计：
- [case-library-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/case-library-design.md)

## 十、持续进化能力

当前已经具备持续更新的结构基础：
- [法规依据体系](/Users/linzeran/code/2026-zn/agent_compliance/docs/product-specs/legal-authority-system.md)
- [案例库设计](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/case-library-design.md)
- [持续更新机制](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/continuous-update-mechanism.md)
- [更新自动化方案](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/update-automation-spec.md)

当前还具备标准化更新模板：
- [月度规则更新摘要模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/monthly-rule-update-template.md)
- [新增案例候选模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/new-case-candidates-template.md)
- [能力缺口评测报告模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/eval-gap-report-template.md)

当前更新机制已明确覆盖四类对象：
- 法律法规和部门规章
- 财政部门政策解读和公开答复
- 中国政府采购网及省级政府采购网典型案例
- 内部审查失败样本和人工修正记录

并已定义周期能力：
- 每周抓取新增案例、政策解读和高频争议点
- 每月复核法规有效性、更新规则映射和 benchmark
- 每季度复盘误报漏报、调整问题分类和提示词、输出能力变化报告

相关设计：
- [continuous-update-mechanism.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/continuous-update-mechanism.md)

## 十一、更新自动化准备能力

当前虽然尚未完全自动化运行，但已经具备较完整的自动化任务设计。

已明确拆分的自动化任务包括：
- 法规与政策扫描
- 案例候选收集
- 能力回归检查

每轮自动化的目标产物已明确为：
- `月度规则更新摘要`
- `新增案例候选清单`
- `能力缺口评测报告`

当前自动化能力强调：
- 先进入候选池和摘要层
- 再经过人工审核
- 最后进入正式法规库、案例库和评测集

这意味着当前系统已经不是“人工临时补知识”的状态，而是具备向半自动、自动化更新机制演进的明确路径。

相关设计：
- [update-automation-spec.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/update-automation-spec.md)

## 十二、评测与能力回归能力

当前体系已明确将评测视为能力建设的一部分，而不是附属工作。

当前已具备或已明确设计的能力包括：
- 将失败样本转成 `docs/evals/` 中的可重复测试案例
- 通过 benchmark 和 rubric 做能力回归检查
- 输出误报、漏报、依据缺失点和能力薄弱点报告
- 将评测结果反向更新到规格、规则、案例库和改写示例中

这意味着系统不只追求“这次看起来答得不错”，还追求“下一轮是否能稳定复现并改进”。

相关模板：
- [能力缺口评测报告模板](/Users/linzeran/code/2026-zn/agent_compliance/docs/generated/templates/eval-gap-report-template.md)

## 十三、工程化协作能力

当前在项目协作层面已形成以下工作方式：
- 每完成一个完整阶段结果后自动提交 Git
- 每完成一个完整阶段结果后默认自动推送远端，除非用户明确要求只保留本地提交
- 提交信息采用结论式表达
- 每轮工作都尽量沉淀到仓库，而不是停留在对话中
- 当前已验证可以将真实审查任务产出沉淀为“正式审查意见 + 结构化 findings + Git 提交记录”的完整闭环

当前还具备 harness 化协作能力：
- 顶层文件简短，便于后续智能体快速扫描
- 执行计划外部化，便于任务中断后续跑
- 设计理由、产品规格、执行计划、评测与生成产物分层存放
- 后续智能体可以直接从仓库状态而不是聊天上下文接力

相关说明：
- [ARCHITECTURE.md](/Users/linzeran/code/2026-zn/agent_compliance/ARCHITECTURE.md)
- [openai-harness-notes.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/references/openai-harness-notes.md)

当前还新增了本地执行骨架能力：
- 已具备可安装的本地 CLI 入口
- 已具备本地 Web 页面入口，支持上传文件、切换缓存与本地模型开关、浏览审查摘要和 findings；对 `docx` 可按段落/表格结构渲染原文，并按 finding 跳转定位到对应位置
- 已具备文档标准化、规则初筛、结果渲染的第一阶段代码骨架
- 已预留 parsers、rules、knowledge、cache、evals 等模块边界，便于后续离线化和算法增强
- 已预留本地大模型兜底接口，默认关闭，显式启用时可用于边界判断和改写增强
- 已形成“代码审查持续逼近人工审查”的增强路线，明确以规则细拆、结构分析、局部模型推理和 benchmark 闭环为主线
- 已补入第一批逼近人工审查的增强规则，可细拆部分资格门槛，并识别评分高权重和中标后补证问题
- 已补入第二批逼近人工审查的增强规则，可识别样品主观高分、商务责任失衡，以及抽检终验与付款联动问题
- 已补入面向正式审查风格的结果聚合增强，可将样品优良中差评分收紧为单个问题点，并压缩相邻商务责任条款的重复命中
- 已补入评分结构分析增强，当样品、认证、业绩等多类高分因素同时出现时，可补出评分结构整体失衡的综合 finding
- 已形成人工式审查查点矩阵，明确资格条件、评分标准、技术要求、商务条款、验收检测、付款违约、模板残留等一级查点及当前代码缺口
- 已补入属地/本地团队/人员画像限制、商务验收付款链路，以及技术要求“需论证”中间层查点，先提升问题找全率而非继续强化评分细算

相关设计：
- [local-runtime-skeleton.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/local-runtime-skeleton.md)
- [human-review-checkpoint-matrix.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/human-review-checkpoint-matrix.md)

## 十四、结果一致性与可复现能力

当前已将“同一输入在相同条件下应输出一致结果”作为正式能力要求。

具体约束包括：
- 同一文件、同一审查范围、同一输出格式、同一法规依据状态、同一本地案例口径状态下，审查结果应尽量保持一致
- 如复审结果与前次结论发生变化，应明确说明变化原因，例如：
  - 输入文件内容发生变化
  - 适用法规或监管口径更新
  - 本地引用资料 `last_verified` 状态变化
  - 输出格式或审查范围发生变化
- 不应在环境和条件未变化时，随意改变问题标题、风险等级、合规判断或修改建议
- 对于需要保持稳定复现的结论，应优先复用既有问题类型、固定输出字段顺序和一致的法条映射口径
- 后续执行优先采用“标准化输入 + 规则版本 + 引用快照 + findings 缓存 + 增量复审”的方式，减少重复全量大模型推理

相关设计：
- [consistency-and-caching-design.md](/Users/linzeran/code/2026-zn/agent_compliance/docs/design-docs/consistency-and-caching-design.md)

## 十五、当前能力边界

当前已经具备的能力：
- 能审查
- 能做文档标准化和定位切分
- 能定位
- 能引用
- 能改写
- 能输出正式审查意见
- 能输出结构化 findings
- 能复用既有审查结果做增量复审
- 能积累案例和失败样本
- 能设计并运行持续更新机制
- 能为自动化更新和能力回归准备标准产物
- 能在本地执行骨架中运行文档标准化、规则初筛和结果输出
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
