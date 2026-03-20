# 政府采购四类专项检查智能体 Product Outline

## Goal
围绕政府采购文件中的四类专项检查事项，形成专项结论、定位证据、风险说明和整改建议，帮助采购人与复核人员快速完成专项核查。

## Agent Metadata
- agent_key: `special_checks`
- template_key: `review`
- agent_type: `review_agent`
- template_label: `review scaffold`

## Inputs
- 采购文件或采购需求文本
- 四类专项检查规则口径
- 正负样例
- 人工专项检查基准

## Outputs
- 四类专项检查结论
- 专项问题列表
- 结构化 findings
- 整改建议
- 导出结果

## First Incubation Focus
- 四类专项检查结构固化
- 专项结论模板统一
- 证据定位与整改建议收束
- 人工专项检查对照

## Notes
- This file is a scaffold draft for early incubation.
- Move the stable version into `docs/product-specs/` when the agent enters productization.
