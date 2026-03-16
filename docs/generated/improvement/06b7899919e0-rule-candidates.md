# 规则候选

## CAND-06B78999-001 样品评分标准主观性强，缺乏量化指标
- issue_type: `ambiguous_requirement`
- source_section: `评标信息-一、评标方法：综合评分法（新价格分算法）-技术要求偏离情况`
- source_text: `1） 评定是否偏离以投标人响应及提供的检测报告是否符合招标技术标准为准， 没有要求提供检测报告的以投标人响应为准。单个产品要求提供的检测报告， 必须在同一份报告中呈现， 否则…`
- trigger_keywords: `同一份报告`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-002 样品评分主观性强且缺少量化锚点
- issue_type: `ambiguous_requirement`
- source_section: `评标信息-一、评标方法：综合评分法（新价格分算法）-技术要求偏离情况`
- source_text: `1） 措施全面很具体、针对性很强、实施流程很清晰合理， 质量标准很具体， 得 80%分；`
- trigger_keywords: `1） 措施全面很具体、针对性很强`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-003 认证评分结构失衡且可比性不足
- issue_type: `scoring_structure_imbalance`
- source_section: `评标信息-一、评标方法：综合评分法（新价格分算法）-技术要求偏离情况`
- source_text: `环境标志产品认证`
- trigger_keywords: `认证`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-004 验收结果单方确定且需求边界开放
- issue_type: `unclear_acceptance_standard`
- source_section: `第二章   招标项目需求-六、项目商务需求-5.4 货物和设备运抵安装现场后，采购人将与投标人共同验收，`
- source_text: `如投标人届时不派人来， 则验收结果应以采购人的验收报告为最终验收结果。验收时发现短缺、破损，采购人有权要求投标人立即补发和负责更换。`
- trigger_keywords: `最终验收结果`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。
