# 能力总览

## 目标定位

本项目当前不是单次问答式审稿助手，而是一个面向政府采购场景的“采购需求合规性审查智能体”可持续进化型工作框架。

统一口径：
- 对外描述时，应同时承认两层含义：
- 一层是“体系化能力框架”，即本项目被设计成具备审查、定位、引用、改写、一致性复审、缓存复用和持续更新能力的政府采购合规审查智能体。
- 一层是“当前已验证交付能力”，即已经能够对真实采购文件执行正文提取、条款切分、结构化审查、正式意见输出、结果落库、Git 留痕与复审复用的完整闭环。

因此，本项目当前已经不是“帮你看一段采购需求有没有问题”的单点能力，而是一套面向采购需求合规性审查的可持续、可复核、可复用的审查体系。

它当前阶段重点不是做争议裁判，而是帮助采购人在发布前：
- 发现风险
- 完成改稿
- 做好复核
- 更放心地把采购需求进行公布

在这个定位下，它逐步形成：
- 可审查
- 可引用
- 可定位
- 可改写
- 可积累
- 可更新
- 可复盘

的一整套能力体系。

## 一、审查能力

当前可以对以下对象进行结构化合规预审：
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

当前统一阶段定位：
- 面向采购人“采购需求形成与发布前审查”阶段
- 重点帮助采购人提前发现不宜发布的高风险条款
- 对边界性问题优先提示“需论证/需复核”，而不是直接做发布后的责任裁判
- 导出结果默认优先服务采购人改稿、发布前复核和留痕
- 置信度校准已开始按“发布前预防型审查”场景，对 `需论证 / 需复核` 类问题做保守校准

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

并已形成第一版结果导出设计：
- 统一支持 `Markdown / Excel / JSON`
- 区分 `主问题版 / 完整明细版`
- 计划由 `review-next` 承接导出入口
- 导出字段直接复用 `Finding`、法规语义层、品目层和证据层结果，不另起旁路数据结构

已建立正式模板：
- [正式审查意见模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/review-output-template.md)
- [业务方/采购人修改用正式审查意见表模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/business-facing-review-table-template.md)

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
- 产出符合 [finding-schema.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/finding-schema.md) 的结构化 JSON 结果
- 支持后续复审直接复用 findings 缓存，而不是重复全量自由推理
- 对已聚合的相邻命中，生成更接近正式审查意见写法的问题标题和统一改写建议
- `review-next` 已开始支持结果导出，第一阶段提供：
  - `Markdown / Excel / JSON`
  - `主问题版 / 完整明细版`
  - 导出字段直接复用 `Finding`、法规语义层、品目层和证据层结果
  - 导出文件会同步落盘到 `docs/generated/exports/`
  - Excel 导出已补入摘要页、冻结首行、自动筛选和按风险等级着色

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
- [consistency-and-caching-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/consistency-and-caching-design.md)
- [code-review-system-technical-description.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-system-technical-description.md)

当前也已补齐两类面向不同读者的说明材料：
- 面向业务和用户的 [code-review-product-introduction.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/code-review-product-introduction.md)
- 面向技术接入的 [code-review-technical-integration.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/code-review-technical-integration.md)
- 面向下一阶段架构增强的 [procurement-catalog-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/procurement-catalog-layer-design.md)，用于引入采购品目目录层、标的标准化识别和混合场景边界判断
- 面向主编排升级的 [code-review-main-pipeline-update.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-main-pipeline-update.md)，用于把品目目录层正式接入代码审查主链路，并重排策略、规则、分析器和仲裁顺序
- 面向下一阶段架构排查的 [architecture-gap-priorities.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/architecture-gap-priorities.md)，用于明确当前真正缺失的架构层与补强优先级，而不是继续零散补规则
- 面向当前持续调优阶段的 [engine-tuning-checklist.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/engine-tuning-checklist.md)，用于明确哪些 engine 是当前高优先级校准项、误判高发点和跨层联动问题
- 面向法规条文级语义增强的 [legal-semantic-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-semantic-layer-design.md)，用于正式设计 `legal_clause_index`、`issue_type_authority_map` 和 `legal_authority_reasoner`
- 面向审查结果交付增强的 [review-export-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/review-export-design.md)，用于统一 `Markdown / Excel / JSON` 三种导出格式，以及 `主问题版 / 完整明细版` 两种导出模式
- 面向规则治理增强的 [rule-governance-layer-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/rule-governance-layer-design.md)，用于定义 `rule_registry`、`rule_priority_profile` 和 `catalog_sensitive_rule_router`

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
- [finding-schema.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/finding-schema.md)
- [location-field-spec.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/location-field-spec.md)

## 五、法规和案例引用能力

当前已经建立了本地可检索知识库，而不是每次临时查找引用。

已具备：
- [法规依据本地引用库](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/legal-authorities/README.md)
- [案例口径本地引用库](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/case-sources/README.md)
- [引用资料索引](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/reference-index.md)

引用资料已逐步具备统一元数据：
- `reference_id`
- `reference_type`
- `source_org`
- `source_url`
- `canonical_registry_url`
- `doc_no`
- `promulgation_date`
- `validity_status`
- `authority_level`
- `verification_source`
- `is_primary_source`
- `status`
- `review_topics`
- `related_rule_ids`
- `related_case_ids`
- `last_verified`
- `last_registry_verified`

当前还具备法规依据分层使用能力：
- 先引用法律和实施条例等高位阶规则
- 再补充财政部规章和管理办法
- 再参考政策解读、官方答复、地方细则和典型案例
- 对法域差异明显、规则有效性待核实的问题，升级为人工复核而不是强行下结论
- 对财政部规章类资料，已开始引入“中国政府采购网-财政部规章”目录作为权威核验层，用于补充令号、颁布日期和有效性状态
- 已开始建立 `data/legal-authorities/` 本地目录结构，为后续权威原文快照和标准化法规文本提供离线存储入口
- 已生成第一版 `data/legal-authorities/index/clause-index.json`，把 `LEGAL-001`、`LEGAL-002` 抽成可检索的条文级索引，为后续 `legal_clause_index`、`issue_type_authority_map` 和 `legal_authority_reasoner` 提供基础数据层
- 已生成第一版 `data/legal-authorities/index/issue-type-authority-map.json`，先把高频 `issue_type` 稳定映射到主依据、辅依据和条文级索引，减少同类问题在不同文件中的法规引用漂移
- 已接入第一版 `legal_authority_reasoner`，开始基于 `issue_type_authority_map + clause-index + 当前 finding` 自动生成主依据、辅依据、适用逻辑，并补充法规侧人工复核理由
- 已接入第一版 `confidence_calibrator`，开始把条文级主依据、问题类型边界和人工复核标记合并进 `confidence` 校准
- `review-next`、规则管理页和 benchmark gate 已开始展示主依据、辅依据、适用逻辑和法规侧复核提示，法规语义层不再只停留在后端
- 已接入规则治理层，开始具备 `rule_registry`、`rule_priority_profile` 和 `catalog_sensitive_rule_router`，并让规则扫描按采购品目优先级压缩同一条款同一风险簇的重复命中；当前已支持正式规则状态分层、按品目显式停用/降权，以及在 `/rules` 页面展示规则治理信息
- 已开始把采购品目层从“分类”推进到“画像”：
  - 已新增体育器材及运动场设施场景，能识别 `全民健身`、`多功能运动场`、`围网`、`硅PU`、`体育比赛用灯` 等官方品目和高频业务表达
  - 品目知识画像已补入“技术评分过高、负偏离扣分过重、专项检测报告加分、轻量智能化边界外扩、品牌定向痕迹”等运动场高风险模式
  - 评分引擎已开始按真实评分表结构识别 `技术部分评分PT`、`商务部分评分PB`、`评审项` 等表达，不再只依赖 `评标信息` 或简单 `评分` 标签
  - 品目知识画像已进入第二阶段，开始提供可执行的 `domain_mismatch_markers`、`template_scope_markers`、`mixed_scope_markers`，并直接参与错位判断、模板残留判断和混合采购边界判断
  - 品目知识画像已继续下沉到 `document_audit_llm`、`confidence_calibrator` 和 benchmark/difference learning：全文辅助扫描提示词会显式带出品目画像高风险和边界提示，置信度校准会结合当前品目画像做轻量升降权，benchmark 与差异学习结果也开始汇总当前场景的画像高风险模式

相关设计：
- [legal-authority-system.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/legal-authority-system.md)

## 六、规则与案例映射能力

当前已经建立两类结构化资产：
- [法规依据库样表](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/legal-authority-library-starter.md)
- [典型案例库样表](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/case-library-starter.md)

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
- [consistency-and-caching-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/consistency-and-caching-design.md)

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

当前还新增了“本地模型参与 -> 规则候选生成 -> benchmark gate”的自动演化链路：
- 启用本地模型后，会额外执行模板错贴与标的域不匹配、评分结构判断、商务链路联合判断三类局部任务
- 当前已开始接入“全文辅助扫描”任务，用于在规则候选不足时补充资格异常、评分内容错位、技术固定年份和商务边界类候选问题
- 全文辅助扫描新增的问题已开始先进入仲裁层，再决定是否上浮为主问题，避免本地模型候选重新把已收束的主问题结构打碎
- 全文辅助扫描兜底已开始从“补零散句子”升级为“补资格章节主问题、评分章节主问题、商务章节主问题”，即使本地模型未返回，也能优先补出更接近人工式审查的章节级风险概括
- 当前已开始落地 `document_level_judgment_engine`，可根据高风险和中风险 findings 的章节分布与主题问题，先形成整份文件的主风险画像，并把主导章节与突出主问题写入 `overall_risk_summary`
- 当前已开始落地 `document_strategy_router`，可先识别文件更偏信息化、药品/医疗配套、货物安装、物业服务还是综合项目，并给出建议优先复核的章节路线。
- 当前已继续增强 `document_strategy_router` 的纺织类货物识别，可把窗帘、隔帘、床品、被服等项目优先识别为“供货 + 安装 + 售后保障”场景，避免因医院名称误判为药品或医用配套采购。
- 当前已继续增强 `document_strategy_router` 和 `mixed_scope_boundary_engine` 的标识标牌及宣传印制服务识别，可把“标识导视/宣传印制 + 印刷设备储备 + 软件著作权/信息化支撑”识别为混合边界问题，而不再仅因医院名称误判为药品或医用配套采购。
- 当前已开始落地 `mixed_scope_boundary_engine`，可在“药品 + 自动化设备 + 信息化接口”等混合采购场景下，把系统对接、自动化配套和附加服务义务收束为单独主问题，而不再只作为普通模板残留碎点出现
- 当前已开始落地 `qualification_reasoning_engine`，可在资格子主题之上进一步生成“资格条件整体超出法定准入和履约必需范围”这类总判断主问题，帮助结果更接近人工对资格章节的整体结论。
- 当前已开始落地 `scoring_semantic_consistency_engine`，可判断评分项名称、评分内容、评分证据和评分目的是否一致，并把方案项混入工程案例、商务项混入一般经营指标、认证项混入跨领域证书等问题收束为单独主问题。
- 当前已继续增强家具货物场景下的评分主题识别，可把“生产设备和制造能力直接高分赋值且与核心履约评价边界不清”“样品评分叠加递交签到和不接收机制形成额外门槛”“认证评分项目过密且高分值集中”等问题稳定上浮为独立主问题，而不再只停留在评分碎点或技术噪声里。
- 当前已开始落地 `personnel_certificate_mismatch_engine`，可进一步识别团队评分中学历、职称、奖项、项目经验和错位证书的堆叠设计。
- 当前已继续增强 `demo_mechanism_engine`，除演示高分值外，还可把可运行系统、原型/PPT 差异、签到时限和现场组织门槛收束为演示机制主问题。
- 当前已开始落地 `commercial_lifecycle_analyzer`，可从付款、验收、复检、售后到场和责任承担全链路识别整体偏重供应商承担的履约后果链。
- 当前已开始落地 `evidence_selector`，可按主问题语义优先挑选更像人工会引用的代表性摘录，而不再仅按前两段原文截取。
- 当前已开始落地 `difference_learning_loop`，启用本地模型后会额外生成结构化学习建议，分别反哺规则、主题分析器、LLM prompt 和 benchmark。
- 本地模型新增的边界问题会自动沉淀成 `rule_candidate`，而不是只停留在一次性 finding 中
- 每个 `rule_candidate` 至少携带：`candidate_rule_id`、`issue_type`、`source_text`、`trigger_keywords`、`suggested_merge_key`、`false_positive_risk`
- `eval` 入口已可直接显示最新 benchmark gate 结果，帮助判断候选问题类型是否已被 benchmark 覆盖
- 当前已补入 `template_mismatch` 问题类型的 benchmark 样本，用于承接模板错贴和标的域错位问题
- 后续主线已明确升级为“条款分类 + 结构分析 + 章节级 LLM 审查辅助 + finding 仲裁 + 规则候选与 benchmark gate”的自动持续优化架构，而不再只是零散补规则
- 当前已开始落地 `scoring_structure_analyzer`，可在 review 后处理阶段把分散的评分类命中进一步收束为章节级主问题，例如：
  - 多个方案评分项大量使用主观分档且缺少量化锚点
  - 现场演示分值过高且签到要求形成额外门槛
  - 商务评分将企业背景和一般财务能力直接转化为高分优势
- 当前已开始落地 `commercial_chain_analyzer`，可把分散的付款、履约评价、整改和解除合同条款进一步收束为商务链路主问题，例如：
  - 付款条件与履约评价结果深度绑定且评价标准开放
- 当前已新增 `qualification_bundle_analyzer`，可把资格章节中的一般财务、规模和属地门槛收束为更接近人工式审查的章节主问题，例如：
  - 资格条件叠加设置一般财务、规模和属地门槛
- 当前已进一步细化 `qualification_bundle_analyzer`，可把一般财务/规模门槛、经营年限/属地场所/单项业绩门槛和行业错位资质拆成更精准的资格子主题，例如：
  - 资格条件设置一般财务和规模门槛
  - 资格条件设置经营年限、属地场所或单项业绩门槛
  - 资格条件中存在与标的域不匹配的行业资质或专门许可
- 当前已继续增强 `qualification_bundle_analyzer`，可在中药配方颗粒等样本中把成立年限、一般纳税、参保人数、资产规模、异地经营场所和错位资格整段归并为资格主问题，而不只依赖单个高频错位词。
- 当前已新增 `brand_and_certification_scoring_analyzer`，可把品牌打分和认证错位从评分碎点上浮为章节级主问题，例如：
  - 评分项直接按品牌档次赋分
  - 认证评分混入与标的不匹配的企业称号和跨领域证书
- 当前已进一步细化 `technical_reference_consistency_engine`，可按改稿需要拆分技术章节中的标准错位和证明形式过严问题，例如：
  - 技术要求引用了与标的不匹配的标准或规范
  - 技术证明材料形式要求过严且带有地方化限制
- 当前已继续增强 `technical_reference_consistency_engine`，能在混合采购场景中同时识别“标准代号错位”和“国家级检测中心/特定报告形式限制”等双重技术风险。
- 当前已进一步细化 `commercial_burden_analyzer`，可把资金占用、交期异常、验收费转嫁和责任失衡分层输出为更利于改稿的商务主问题，例如：
  - 商务条款设置异常资金占用安排
  - 交货期限设置异常或明显失真
  - 验收送检、检测和专家评审费用整体转嫁给供应商
  - 商务责任和违约后果设置明显偏重
- 当前已继续增强 `commercial_burden_analyzer`，可单独识别“履约担保验收后自动转售后保证金、长期占压至质保期结束”这类异常资金占用安排。
- 当前已继续增强 `domain_match_engine`，开始支持“药品 + 自动化设备 + 信息化接口”这类混合采购场景的边界判断，能区分合理配套设备要求与超出药品采购边界的系统对接、运维清洁义务。
- 当前已形成“采购品目目录层”设计方案，后续将引入 `procurement_catalog_classifier` 和最小可用品目集，在 `document_strategy_router -> domain_match_engine -> analyzers` 之间补入标的标准化识别、品目知识映射和混合场景边界校准能力。
- 当前已开始落地 `procurement_catalog_classifier` 和最小可用品目集，可在文件级摘要中输出主品目、次品目和混合采购提示，并将 `furniture_goods`、`textile_goods`、`property_service`、`information_system`、`medical_device_goods`、`medical_tcm`、`signage_printing_service`、`equipment_installation`、`catering_service` 等高频场景纳入统一识别入口。
- 当前主编排已正式接入品目分类结果：`review.py` 会先完成 `procurement_catalog_classifier` 识别，再把同一份分类结果传入 `review_strategy.py`，用于生成文件级策略画像、章节复核路线和分析器执行顺序，而不再只是作为摘要展示字段。
- 当前 `domain_match_engine` 与高频 `qualification / scoring / technical / commercial` 分析器也已开始按主品目、次品目和混合采购标记做差异化判断，不再只按固定顺序和通用规则做统一分析。
- 当前 `qualification_reasoning_engine` 和 `finding_arbiter` 也已开始参考官方品目编码前缀控制资格总问题上浮和主题覆盖边界，能够更稳地区分物业、标识印制、医疗设备等场景下哪些错位证书和门槛应独立上浮、哪些不应被总问题过度吞并。
- 当前官方品目编码映射结果也已继续下沉到 `document_audit_llm` 和 `evidence_selector`：全文辅助扫描会在提示词里显式带出主品目、官方品目映射和混合采购提示，代表性证据选择也会结合品目场景优先保留更具诊断价值的原文摘录。
- 当前官方品目编码映射结果也已继续下沉到 `rule_candidates` 和 `difference_learning_loop`：本地模型新增问题生成的规则候选、benchmark 建议和差异学习建议会同时带上主品目、审查领域和混合采购标记，便于后续按场景补规则、补分析器和补 benchmark。
- 当前已新增第一版品目知识画像层 `catalog-knowledge-profiles.json` 和 `catalog_knowledge_profile.py`，开始把“常见合理要求 / 高风险画像 / 常见错位线索 / 边界说明 / 优先 analyzer”从分类数据中独立出来，并供 `review_strategy` 的摘要与 analyzer 路由消费。
- `benchmark gate` 和规则管理页也开始按品目场景展示候选规则：现在可以直接看到某条候选规则属于哪个主品目、审查领域以及是否属于混合采购场景，方便按场景确认入库和后续补 benchmark。
- 当前已把 2022 版《政府采购品目分类目录》原始 PDF 快照纳入 `data/procurement-catalog/raw/full-catalog-2022/`，为后续生成全量 `catalogs-full.json` 和审查映射层提供本地权威来源。
- 当前已基于该 PDF 生成第一版 `data/procurement-catalog/catalogs-full.json` 全量目录骨架，可直接用于品目编码、层级、父子关系和主次品目识别增强。
- 当前已新增 `data/procurement-catalog/review-domain-map.json` 第一版审查领域映射，用官方品目编码和前缀先覆盖家具、被服、物业、信息化、医疗设备、药品配套、标识印制、设备安装、餐饮等高频场景。
- 当前已补入餐饮托管/食堂运营服务场景识别，可在医院、学校或公共机构食堂项目中优先按“评分标准 -> 商务与验收 -> 技术要求”的路线复核，并避免将“24小时营业及就餐服务”等持续供餐义务误判为属地限制。
- 当前已补入 `geographic_tendency_analyzer`、`acceptance_boundary_analyzer`、`industry_appropriateness_analyzer` 和 `theme_splitter_and_summarizer`，可进一步识别：
  - 驻场、短时响应或服务场地要求形成事实上的属地倾斜
  - 验收程序、复检与最终确认边界不清
  - 评分和技术要求中存在行业适配性不足的错位内容
- 当前已继续增强 `finding_arbiter`，可进一步压掉正文与投标文件格式附件中的语义重复问题，并优先保留更适合改稿的正文主问题和代表性证据；对物业服务项目，也已开始过滤投标工具说明、信息公开说明等模板编制提示对主问题的污染。
- 当前已继续增强 `qualification_reasoning_engine`、`scoring_semantic_consistency_engine` 和 `commercial_lifecycle_analyzer` 在医院物业服务样本中的表现，可区分供应商准入与岗位持证、单独上浮“医院物业经验和医院评审经验高权重”主题，并更稳定识别“管理费直接挂钩、标准可修订、扣罚与终止并行”的商务链路问题。
- 当前已继续增强 `technical_necessity_explainer`，在“需论证”类技术问题中开始明确补充必要性、市场可得性、适用标准和建议论证方向，而不只停留在笼统提醒。
- 当前已继续增强 `commercial_lifecycle_analyzer`、`scoring_semantic_consistency_engine` 和 `evidence_selector` 在食堂托管服务样本中的协同表现，可把“月度满意度与服务费挂钩、按比例扣减、保险和人员证书高分堆叠、同类食堂业绩叠加优/优秀履约评价”等问题收束为更接近人工审查的主题主问题与代表性证据。

相关设计：
- [case-library-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/case-library-design.md)

## 十、持续进化能力

当前已经具备持续更新的结构基础：
- [法规依据体系](https://github.com/zeranlin/agent_compliance/blob/main/docs/product-specs/legal-authority-system.md)
- [案例库设计](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/case-library-design.md)
- [持续更新机制](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/continuous-update-mechanism.md)
- [更新自动化方案](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/update-automation-spec.md)

当前还具备标准化更新模板：
- [月度规则更新摘要模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/monthly-rule-update-template.md)
- [新增案例候选模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/new-case-candidates-template.md)
- [能力缺口评测报告模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/eval-gap-report-template.md)

当前更新机制已明确覆盖四类对象：
- 法律法规和部门规章
- 财政部门政策解读和公开答复
- 中国政府采购网及省级政府采购网典型案例
- 内部审查失败样本和人工修正记录

当前还新增了“规则候选自动生长”的中间层：
- 对本地模型在真实文件中新增、而规则链路尚未稳定覆盖的问题，自动生成规则候选
- 规则候选不会直接进入正式规则库，而是先进入 `docs/generated/improvement/` 产物层
- 候选规则需先通过 benchmark gate，再进入后续人工确认入库环节

并已定义周期能力：
- 每周抓取新增案例、政策解读和高频争议点
- 每月复核法规有效性、更新规则映射和 benchmark
- 每季度复盘误报漏报、调整问题分类和提示词、输出能力变化报告

相关设计：
- [continuous-update-mechanism.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/continuous-update-mechanism.md)

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
- [update-automation-spec.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/update-automation-spec.md)

## 十二、评测与能力回归能力

当前体系已明确将评测视为能力建设的一部分，而不是附属工作。

当前已具备或已明确设计的能力包括：
- 将失败样本转成 `docs/evals/` 中的可重复测试案例
- 通过 benchmark 和 rubric 做能力回归检查
- 输出误报、漏报、依据缺失点和能力薄弱点报告
- 将评测结果反向更新到规格、规则、案例库和改写示例中
- 输出最新 `benchmark_gate`，识别哪些新增候选问题类型已被 benchmark 覆盖、哪些仍需先补样本

这意味着系统不只追求“这次看起来答得不错”，还追求“下一轮是否能稳定复现并改进”。

相关模板：
- [能力缺口评测报告模板](https://github.com/zeranlin/agent_compliance/blob/main/docs/generated/templates/eval-gap-report-template.md)

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
- [ARCHITECTURE.md](https://github.com/zeranlin/agent_compliance/blob/main/ARCHITECTURE.md)
- [openai-harness-notes.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/references/openai-harness-notes.md)

当前还新增了本地执行骨架能力：
- 已具备可安装的本地 CLI 入口
- 已具备本地 Web 页面入口，支持上传文件、切换缓存与本地模型开关、浏览审查摘要和 findings；对 `docx` 可按段落/表格结构渲染原文，并按 finding 跳转定位到对应位置
- 已新增独立的审查工作台 V2 页面，可单独展示章节级主问题、来源链路、模型新增问题和文档联动定位，而不影响原有审查页
- 已在 Web 页面补入规则管理区，可查看候选规则、benchmark gate 状态，并记录“确认入库 / 暂缓 / 忽略”决策
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
- 已补入评分项中的属地限制识别，并开始识别单方解除、违约金、扣款条件等商务失衡条款；技术“需论证”类 finding 也开始按主题归并
- 已将窗帘项目中的人工差异要点整理为 benchmark 回归样本，后续可持续验证属地、类似业绩前置、商务违约链路和技术需论证查点
- 已让本地 eval 入口读取 benchmark 清单；同时补入服务响应条款中的属地限制，并继续压缩技术“需论证”类 finding
- 已开始把资格异常识别、评分内容错位识别和全文辅助扫描纳入正式主链路，不再只依赖单个项目差异驱动补规则
- 已把原先落在 `other` 里的资格错位和评分错位细分成更稳定的问题类型，如 `qualification_domain_mismatch` 与 `scoring_content_mismatch`
- 已启动标的域匹配分析，可围绕项目信息化、纺织品、设备安装等主标的域，归并生成“资格条件中存在与标的域不匹配的资质或登记要求”“评分项中存在与标的域不匹配的证书认证或模板内容”“文件中存在与标的域不匹配的模板残留或义务外扩”等主题级主问题
- 已启动 finding 仲裁层，可在主题级主问题生成后，自动压掉被其完整覆盖的评分碎点和商务碎点，让最终输出更接近“少数主问题 + 代表性证据”的人工式审查结构
- 已把固定年份这类技术“需论证”问题提升为主题级 finding，并增强了必要性论证、市场可得性和更中性表达的说明质量
- 已补入 `1 小时到场 / 60 分钟到场` 等事实上的属地倾斜识别，并在标题层直接提示“售后响应时限设置形成事实上的属地倾斜”
- 已继续补强属地/响应时限、认证/品牌/荣誉、资金占用/验收费/责任失衡三组高频显性规则，并同步收紧 `geographic_tendency_analyzer`、`brand_and_certification_scoring_analyzer`、`commercial_burden_analyzer` 和 `finding_arbiter`，减少新增命中把结果再次打碎
- 已继续压缩长文档中的本地模型重复输出和错位挂接，改为优先使用 `clause_ref=行号:条款编号`，并按问题类型、行号和摘要签名做去重

相关设计：
- [local-runtime-skeleton.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/local-runtime-skeleton.md)
- [human-review-checkpoint-matrix.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/human-review-checkpoint-matrix.md)

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
- [consistency-and-caching-design.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/consistency-and-caching-design.md)

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
