# 规则候选

## CAND-06B78999-001 采购标的与条款内容严重错位（服务混入货物）
- issue_type: `other`
- source_section: `第二章   招标项目需求-六、项目商务需求-其他`
- source_text: `供应商提供包括公共区域、室外公共场所、地面、通道、楼层、天台、办公室、功能室等室内的卫生清洁、保洁，垃圾的分类收集、清运`
- trigger_keywords: `保洁, 清运`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-002 技术参数与采购标的类型不匹配（硬件混入）
- issue_type: `other`
- source_section: `第二章   招标项目需求-五、具体技术要求-1.2 织物密度（根/10cm） ：经密 830-840 纬密 455-465；`
- source_text: `1.2 织物密度（根/10cm） ：经密 830-840 纬密 455-465；`
- trigger_keywords: `1.2 织物密度（根/10cm）`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-003 系统功能要求与货物采购不符（软件/系统混入）
- issue_type: `other`
- source_section: `第二章   招标项目需求-五、具体技术要求-1.3 纱线线密度：经纱（1）12-15tex、经纱（2）12-15tex*2、纬纱 10-13tex；`
- source_text: `1.3 纱线线密度：经纱（1）12-15tex、经纱（2）12-15tex*2、纬纱 10-13tex；`
- trigger_keywords: `1.3 纱线线密度：经纱（1）1`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-004 商务需求模板残留（医院系统对接）
- issue_type: `other`
- source_section: `第二章   招标项目需求-六、项目商务需求-5.4 货物和设备运抵安装现场后，采购人将与投标人共同验收，-其他`
- source_text: `★9.6 中标人提供的芯片及系统需无缝对接医院现有的设备及系统，以保障正常运行。`
- trigger_keywords: `芯片, 系统`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-005 义务外扩（开放式验收标准）
- issue_type: `other`
- source_section: `第二章   招标项目需求-六、项目商务需求-5.4 货物和设备运抵安装现场后，采购人将与投标人共同验收，-其他`
- source_text: `求不符，以采购人的实际需求为准。`
- trigger_keywords: `实际需求为准`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-006 样品评分主观性强且缺少量化锚点
- issue_type: `ambiguous_requirement`
- source_section: `评标信息-一、评标方法：综合评分法（新价格分算法）-技术要求偏离情况`
- source_text: `1） 措施全面很具体、针对性很强、实施流程很清晰合理， 质量标准很具体， 得 80%分；`
- trigger_keywords: `1） 措施全面很具体、针对性很强`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-007 认证评分结构失衡且可比性不足
- issue_type: `scoring_structure_imbalance`
- source_section: `评标信息-一、评标方法：综合评分法（新价格分算法）-技术要求偏离情况`
- source_text: `环境标志产品认证`
- trigger_keywords: `认证`
- false_positive_risk: `low`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-008 验收结果单方确定且需求边界开放
- issue_type: `unclear_acceptance_standard`
- source_section: `第二章   招标项目需求-六、项目商务需求-5.4 货物和设备运抵安装现场后，采购人将与投标人共同验收，`
- source_text: `如投标人届时不派人来， 则验收结果应以采购人的验收报告为最终验收结果。验收时发现短缺、破损，采购人有权要求投标人立即补发和负责更换。`
- trigger_keywords: `最终验收结果`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。
