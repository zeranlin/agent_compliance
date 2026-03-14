# 初始基准样例集

## 目的

这组初始样例用于对采购合规智能体进行压力测试，覆盖明显违规、明显可接受以及需要判断的边界场景。

## 样例格式

每个案例包含：
- `case_id`
- `scenario`
- `input_clause`
- `expected_core_outcome`
- `expected_issue_type`
- `expected_severity`
- `expected_escalation`

## 案例列表

### 案例 C-001

- `scenario`: 直接锁定品牌型号
- `input_clause`: `投标产品必须为A品牌X2000型号服务器，不接受其他品牌替代。`
- `expected_core_outcome`: 应判定为大概率不合规，因为其直接限制品牌和型号，且没有等效表述
- `expected_issue_type`: `brand_or_model_designation`
- `expected_severity`: `3`
- `expected_escalation`: `false`

### 案例 C-002

- `scenario`: 虽有等效表达但仍过于含糊的品牌导向
- `input_clause`: `投标产品应采用国际知名品牌，参考A品牌、B品牌或同档次产品。`
- `expected_core_outcome`: 应标记为存在问题，因为条款仍以品牌为锚点，且“同档次”缺乏明确标准
- `expected_issue_type`: `brand_or_model_designation`
- `expected_severity`: `2`
- `expected_escalation`: `false`

### 案例 C-003

- `scenario`: 中性的性能参数
- `input_clause`: `设备应支持不少于128GB内存，满足本项目并发数据处理需求。`
- `expected_core_outcome`: 应判定为大概率合规，因为它是面向性能的、且表面上可衡量
- `expected_issue_type`: `other`
- `expected_severity`: `0`
- `expected_escalation`: `false`

### 案例 C-004

- `scenario`: 可疑的过窄技术区间
- `input_clause`: `显示屏尺寸须为23.8英寸，允许偏差不超过0.1英寸。`
- `expected_core_outcome`: 应标记为存在风险，因为过窄区间可能只匹配少数产品，且未说明功能必要性
- `expected_issue_type`: `narrow_technical_parameter`
- `expected_severity`: `2`
- `expected_escalation`: `true`

### 案例 C-005

- `scenario`: 不合理的属地机构要求
- `input_clause`: `供应商须在采购人所在地行政区域内设有分公司，否则投标无效。`
- `expected_core_outcome`: 应判定为大概率不合规，因为它设置了与履约无明显关联的地域限制
- `expected_issue_type`: `geographic_restriction`
- `expected_severity`: `3`
- `expected_escalation`: `false`

### 案例 C-006

- `scenario`: 过高的历史业绩门槛
- `input_clause`: `供应商近三年须具有不少于10个与本项目完全相同的政府项目业绩。`
- `expected_core_outcome`: 应判定为大概率不合规，因为过高门槛和“完全相同”要求可能排除具备能力的供应商
- `expected_issue_type`: `excessive_supplier_qualification`
- `expected_severity`: `3`
- `expected_escalation`: `false`

### 案例 C-007

- `scenario`: 与履约无直接关系的强制奖项要求
- `input_clause`: `投标人须获得省级及以上质量奖项，否则视为资格不满足。`
- `expected_core_outcome`: 应判定为大概率不合规，因为奖项通常不能直接证明履约能力
- `expected_issue_type`: `irrelevant_certification_or_award`
- `expected_severity`: `3`
- `expected_escalation`: `false`

### 案例 C-008

- `scenario`: 评分项重复放大资格优势
- `input_clause`: `投标人具有ISO9001认证得3分，具有省级质量奖得5分，具有AAA信用等级得5分。`
- `expected_core_outcome`: 应标记为存在问题，因为对非必要认证和荣誉进行高分奖励可能扭曲竞争
- `expected_issue_type`: `duplicative_scoring_advantage`
- `expected_severity`: `2`
- `expected_escalation`: `false`

### 案例 C-009

- `scenario`: 模糊的验收要求
- `input_clause`: `项目建成后应达到先进水平，并保证采购人满意后组织验收。`
- `expected_core_outcome`: 应标记为存在问题，因为验收标准带有主观性且不可验证
- `expected_issue_type`: `unclear_acceptance_standard`
- `expected_severity`: `2`
- `expected_escalation`: `false`

### 案例 C-010

- `scenario`: 缺乏上下文说明的兼容性限制
- `input_clause`: `为保证与现有平台无缝衔接，投标产品必须与现运行系统核心模块完全一致。`
- `expected_core_outcome`: 应标记风险并升级复核，因为兼容性限制可能有正当性，但当前条款过于严格且缺少技术依据或等效路径
- `expected_issue_type`: `brand_or_model_designation`
- `expected_severity`: `2`
- `expected_escalation`: `true`

### 案例 C-011

- `scenario`: 带有可量化目标的服务响应条款
- `input_clause`: `供应商应提供7×24小时技术支持，故障报修后2小时内响应，24小时内提出解决方案。`
- `expected_core_outcome`: 应判定为大概率合规，因为该服务条款可量化且与履约直接相关
- `expected_issue_type`: `other`
- `expected_severity`: `0`
- `expected_escalation`: `false`

### 案例 C-012

- `scenario`: 单方失衡的违约责任
- `input_clause`: `如供应商延期1日，按合同总价10%支付违约金；采购人延期付款不承担任何责任。`
- `expected_core_outcome`: 应标记为存在问题，因为该条款明显单方失衡，商业上可能不合理
- `expected_issue_type`: `one_sided_commercial_term`
- `expected_severity`: `2`
- `expected_escalation`: `true`

## 建议用法

- 先逐条运行智能体处理每个案例。
- 将结构化输出与 `expected_core_outcome`、问题类型、严重度、升级判断进行对比。
- 将误判结果整理为评测报告，存放到 `docs/evals/reports/` 中。
