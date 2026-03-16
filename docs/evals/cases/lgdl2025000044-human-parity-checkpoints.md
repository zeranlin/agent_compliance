# LGDL2025000044 人工逼近查点

## Case 1

- `case_id`: `lgdl2025000044-template-mismatch-service`
- `source_document`: `[LGDL2025000044-A]低值易耗物品采购.docx`
- `source_clause`: `供应商提供包括公共区域、室外公共场所、地面、通道、楼层、天台、办公室、功能室等室内的卫生清洁、保洁，垃圾的分类收集、清运`
- `expected_issue_type`: `template_mismatch`
- `expected_risk_level`: `medium`
- `expected_judgment`: `potentially_problematic`
- `why_expected`: 货物采购文件中混入保洁与垃圾清运服务义务，属于跨标的模板残留。

## Case 2

- `case_id`: `lgdl2025000044-template-mismatch-system`
- `source_document`: `[LGDL2025000044-A]低值易耗物品采购.docx`
- `source_clause`: `★9.6 中标人提供的芯片及系统需无缝对接医院现有的设备及系统，以保障正常运行。`
- `expected_issue_type`: `template_mismatch`
- `expected_risk_level`: `medium`
- `expected_judgment`: `potentially_problematic`
- `why_expected`: 低值易耗物品采购中混入系统对接义务，明显偏向信息化或设备集成场景。

## Case 3

- `case_id`: `lgdl2025000044-template-mismatch-template`
- `source_document`: `[LGDL2025000044-A]低值易耗物品采购.docx`
- `source_clause`: `“开标一览表”中“完工期”一栏的填写内容不作任何要求，由投标人自行填写。`
- `expected_issue_type`: `template_mismatch`
- `expected_risk_level`: `medium`
- `expected_judgment`: `potentially_problematic`
- `why_expected`: 货物采购中使用“完工期”表述，疑似工程或服务类模板残留。
