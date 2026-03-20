from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    IncubationStage,
    SampleSet,
    ValidationComparison,
    create_incubation_run,
)
from agent_compliance.incubator.run_store import (
    load_incubation_run,
    serialize_incubation_run,
    write_incubation_run,
)


class RunStoreTests(unittest.TestCase):
    def test_serialize_and_load_incubation_run_round_trip(self) -> None:
        run = create_incubation_run("compliance_review", "合规智能体第一轮孵化")
        run.set_stage_status(IncubationStage.SAMPLE_PREPARATION, "completed")
        run.add_sample_set(
            IncubationStage.SAMPLE_PREPARATION,
            SampleSet(name="第一批样例", positive_examples=("p1",)),
        )
        run.add_comparison(
            IncubationStage.PARITY_VALIDATION,
            ValidationComparison(
                sample_id="case-001",
                human_baseline="人工",
                strong_agent_result="强智能体",
                target_agent_result="目标智能体",
                gap_points=("评分问题漏判",),
            ),
        )
        run.add_recommendation(
            IncubationStage.DISTILLATION_ITERATION,
            DistillationRecommendation(
                recommendation_key="case-001:score-gap",
                title="增强评分语义",
                target_layer="scoring_semantic_consistency_engine",
                action="补评分结构失衡上浮逻辑",
                rationale="目标智能体漏判",
                status="accepted",
                resolution_notes="纳入下一轮实现",
            ),
        )

        payload = serialize_incubation_run(run)
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_incubation_run(Path(temp_dir), "compliance_review", "run-001", run)
            loaded = load_incubation_run(paths.manifest_path)

        self.assertEqual(payload["agent_key"], "compliance_review")
        self.assertEqual(loaded.run_title, "合规智能体第一轮孵化")
        self.assertEqual(
            loaded.get_stage(IncubationStage.SAMPLE_PREPARATION).sample_sets[0].name,
            "第一批样例",
        )
        self.assertEqual(
            loaded.get_stage(IncubationStage.PARITY_VALIDATION).comparisons[0].sample_id,
            "case-001",
        )
        loaded_recommendation = loaded.get_stage(IncubationStage.DISTILLATION_ITERATION).recommendations[0]
        self.assertEqual(loaded_recommendation.recommendation_key, "case-001:score-gap")
        self.assertEqual(loaded_recommendation.status, "accepted")


if __name__ == "__main__":
    unittest.main()
