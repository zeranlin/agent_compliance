# 规则候选

## CAND-06B78999-001 货物采购中混入服务义务条款
- issue_type: `template_mismatch`
- source_section: `第二章   招标项目需求-六、项目商务需求-其他`
- source_text: `供应商提供包括公共区域、室外公共场所、地面、通道、楼层、天台、办公室、功能室等室内的卫生清洁、保洁，垃圾的分类收集、清运`
- trigger_keywords: `保洁, 清运`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-002 特定医院系统对接要求与采购标的不符
- issue_type: `template_mismatch`
- source_section: `第二章   招标项目需求-六、项目商务需求-5.4 货物和设备运抵安装现场后，采购人将与投标人共同验收，-其他`
- source_text: `★9.6 中标人提供的芯片及系统需无缝对接医院现有的设备及系统，以保障正常运行。`
- trigger_keywords: `芯片, 系统`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-003 技术参数与采购标的领域错位
- issue_type: `template_mismatch`
- source_section: `第二章   招标项目需求-五、具体技术要求-1.2 织物密度（根/10cm） ：经密 830-840 纬密 455-465；`
- source_text: `1.2 织物密度（根/10cm） ：经密 830-840 纬密 455-465；`
- trigger_keywords: `1.2 织物密度（根/10cm）`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。

## CAND-06B78999-004 政策附件内容模板残留
- issue_type: `template_mismatch`
- source_section: `第十二章    附件：相关政策`
- source_text: `三、本规定适用的行业包括： 农、林、牧、渔业， 工业（包括采矿业， 制造 业， 电力、热力、燃气及水生产和供应业），建筑业， 批发业，零售业，交通运输 业（不含铁路运输业），…`
- trigger_keywords: `三、本规定适用的行业包括： 农、`
- false_positive_risk: `medium`
- generation_reason: LLM 在 review 阶段新增了该问题点，当前规则链路未稳定覆盖。
