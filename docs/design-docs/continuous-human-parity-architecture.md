# 代码审查持续逼近人工审查的自动优化架构

## 背景

当前代码审查已经具备：
- 文档标准化
- 高频规则扫描
- 本地知识检索
- 结构化 findings 输出
- 局部本地模型辅助
- 规则候选生成
- benchmark gate

但在真实文件上，代码结果与人工式审查仍存在稳定差异，主要体现在：
- 代码更偏逐条命中，人工更偏章节级主问题归并
- 代码对评分表、演示机制、付款与履约评价的“组合逻辑”理解仍弱于人工
- 代码对模板错贴、错位证书和条款域不匹配的识别，还更多依赖高频词而不是语义匹配
- 代码对商务链路、评分结构和现场组织要求的综合判断还不够稳定

因此，后续目标不应再只是“继续补规则”，而应升级成一条可自动持续优化的审查主链路。

## 目标

建立一条以“自动审查 + 自动生成优化材料 + benchmark 验证 + 人工仅确认入库”为核心的闭环，使代码审查持续逼近人工式审查。

统一目标：
- 单次审查过程中不依赖人工参与
- 代码结果逐步从“条款扫描器”升级为“章节级审查员”
- 模型参与发现新问题，但不直接替代最终裁判
- 候选规则和候选知识可自动生长，但正式入库仍保留人工确认

## 总体架构

目标链路：

`文档解析 -> 条款分类 -> 规则初筛 -> 结构分析 -> 章节级 LLM 审查辅助 -> finding 仲裁 -> 规则候选生成 -> benchmark gate -> 人工确认入库`

### 1. 文档解析层

职责：
- 从 `docx/pdf/txt` 提取稳定文本
- 保留章节、段落、表格、行号、页码、块编号
- 为后续条款分类和章节级归并提供稳定输入

输出：
- `normalized_text`
- `section_map`
- `clause_map`
- `page_map`
- `line_map`
- `doc_blocks`

### 2. 条款分类层

职责：
- 先把条款识别成业务审查对象，而不是直接进入规则命中

建议标准分类：
- `qualification`
- `scoring`
- `demo`
- `technical`
- `commercial`
- `acceptance`
- `payment`
- `performance_evaluation`
- `other`

目标：
- 让规则和模型都在“已知条款类型”的前提下工作
- 为后续章节级总结打基础

### 3. 规则初筛层

职责：
- 抓显性高频问题
- 给后续结构分析和模型辅助提供候选问题

重点不再只是补关键词，而是按主题建设规则包：
- `qualification_anomaly_engine`
- `scoring_content_mismatch_engine`
- `scoring_subjective_grading_engine`
- `demo_mechanism_risk_engine`
- `commercial_chain_precheck_engine`
- `domain_mismatch_precheck_engine`

典型高频主题：
- 一般财务门槛
- 经营年限门槛
- 企业规模、资本、利润、营收转评分
- 奖项荣誉和认证高分
- 方案评分主观分档
- 可运行系统演示高分
- 到场/签到要求
- 单方履约评价与付款绑定
- 模板残留
- 错位证书

### 4. 结构分析层

职责：
- 从“逐条命中”升级到“理解条款组结构”

建议优先建设三类结构分析器：

#### 4.1 评分结构分析器

能力目标：
- 识别评分项类别
- 识别单项分值和累计分值
- 识别主观分档
- 识别同类问题集中出现

重点回答：
- 整张评分表是不是结构失衡
- 同类高分项是不是重复堆叠
- 某一评分项内容是否与评分项名称不一致
- 奖项、证书、项目经验是否被堆叠成包装型竞争优势

#### 4.2 演示机制分析器

能力目标：
- 把演示内容、演示形式、到场签到、时间限制、演示得分联动起来判断

重点回答：
- 演示分值是否过高
- 可运行系统和原型/PPT差距是否过大
- 现场签到与得分是否形成事实性门槛
- 是否对既有系统成熟度、本地组织能力形成明显倾斜

#### 4.3 商务链路分析器

能力目标：
- 把付款、履约评价、整改、扣款、终止合同、验收联动判断

重点回答：
- 付款是否被单方评价控制
- 评价标准是否开放
- 扣款和解除合同条件是否过于单方
- 验收和付款的触发条件是否明确

### 5. LLM 审查辅助层

原则：
- 需要 LLM，但不让 LLM 直接当最终裁判
- 只让 LLM 做“章节理解、候选发现、边界判断”

分成三层：

#### 5.1 局部 LLM

输入：
- 单个评分项
- 单个资格段
- 单个商务条款组

职责：
- 判断该条是否成立
- 判断该条更适合归到哪个 `issue_type`
- 补充风险逻辑和建议改写

#### 5.2 章节级 LLM

输入：
- 整张评分表
- 整段演示规则
- 整段付款与履约评价条款

职责：
- 输出章节级主题问题
- 把碎片命中归并成更像人工意见的主问题
- 判断是否存在“组合后才成立”的风险

#### 5.3 全文辅助扫描 LLM

输入：
- 整份标准化文档

职责：
- 只输出：
  - `candidate_findings`
  - `suspicious_sections`
  - `possible_domain_mismatch`
  - `possible_missing_rules`

约束：
- 不能直接写入最终 findings
- 必须进入仲裁层二次筛选

### 6. finding 仲裁层

职责：
- 合并规则结果、结构分析结果、LLM 候选结果
- 去重
- 拆分
- 归并
- 定级

目标：
- 从“22 条评分碎点”压成“4-7 条章节级主问题”
- 同时保留关键证据位置和代表性摘录

仲裁策略建议：
- 规则命中的结论优先保留
- LLM 新增问题必须保留来源和置信度
- 同一章节内同类问题优先归并
- 不同章节但同一主题的，允许做主题级归并后保留多个代表性条款

## 自动持续优化闭环

目标闭环：

`审查结果 -> 差异样本 -> 规则候选 -> benchmark gate -> 人工确认入库 -> 正式规则/案例/提示词更新`

### 1. 差异样本沉淀

每次真实文件审查后，沉淀以下差异：
- `missed_issue`
- `false_positive`
- `over_fragmented_finding`
- `over_merged_finding`
- `wrong_issue_type`
- `weak_reasoning`

差异样本至少应包含：
- 原文片段
- 条款位置
- 人工结论
- 代码结论
- 差异标签
- 建议归因

### 2. 规则候选生成

来源：
- LLM 新增问题
- 人工与代码差异样本
- benchmark 漏判

输出：
- `candidate_rule_id`
- `issue_type`
- `pattern`
- `trigger_examples`
- `false_positive_risk`
- `suggested_merge_key`
- `recommended_scope`

### 3. benchmark gate

规则候选不能直接转正，必须先过 gate。

gate 需要回答：
- 是否提升了已知漏判召回
- 是否引入明显误报
- 是否导致 finding 过碎
- 是否导致章节归并质量下降

### 4. 人工确认入库

人工只参与这一环：
- 确认规则候选是否转正式规则
- 确认案例是否转 benchmark
- 确认引用资料是否转正式知识库

不参与单次审查过程。

## 关键设计原则

### 1. 不按单个项目补洞

不建议按“柴油发电机项目增强”“窗帘项目增强”这种方式逐个补。

优先补的是通用能力：
- 评分结构
- 商务链路
- 标的域/条款域匹配
- 演示机制
- 章节级归并

### 2. 不让 LLM 直接拍板

全文 LLM 只能做候选发现器和章节总结器，不直接替代规则和仲裁层。

### 3. 规则优先，模型补边界

推荐比例：
- 70% 靠规则、结构分析、仲裁
- 30% 靠模型补章节判断、组合逻辑和候选发现

### 4. 每轮增强必须可回归验证

如果没有 benchmark gate，就很难判断：
- 是真的变强了
- 还是只是换了表达方式

## 分阶段落地建议

### P0

- 落地 `scoring_structure_analyzer`
- 落地 `commercial_chain_analyzer`
- 落地 `document_audit_llm`
- 落地 `finding_arbiter`
- 落地 `domain_match_engine`

完成标志：
- 真实文件上的结果开始从“评分碎点”收束为章节级主问题
- 付款与履约评价绑定、演示签到门槛、错位证书等问题能稳定成点

### P1

- 落地 `demo_mechanism_engine`
- 落地 `personnel_certificate_mismatch_engine`
- 增强“需论证”类说明质量
- 增强长文档 LLM 去重和定位稳定性

完成标志：
- 演示机制、人员包装、属地倾向等问题在真实长文档中稳定召回

### P2

- 自动差异标注
- 自动规则候选归纳
- benchmark 自动回归报告
- 规则管理页完善入库流转

完成标志：
- 模型新增问题能稳定转成候选规则
- 人工只需要在规则管理页确认是否入库

## 与当前能力的关系

这份方案不是替代现有设计，而是在现有基础上继续升级：
- 继承现有离线标准化、规则扫描、局部模型、规则候选和 benchmark gate
- 把后续重点从“继续补散点规则”转向“章节级审查、自动生长、自动验证”

相关文档：
- [review-orchestrator-upgrade.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/review-orchestrator-upgrade.md)
- [code-review-to-human-parity-roadmap.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/code-review-to-human-parity-roadmap.md)
- [human-review-checkpoint-matrix.md](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/human-review-checkpoint-matrix.md)
