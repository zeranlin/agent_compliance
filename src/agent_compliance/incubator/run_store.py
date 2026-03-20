from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from agent_compliance.incubator.lifecycle import (
    DistillationRecommendation,
    IncubationRun,
    IncubationStage,
    IncubationStageRecord,
    SampleSet,
    ValidationComparison,
)


@dataclass(frozen=True)
class IncubationRunPaths:
    """描述一次孵化运行记录的落盘路径。"""

    target_dir: Path
    manifest_path: Path


def write_incubation_run(
    output_dir: Path,
    agent_key: str,
    run_key: str,
    run: IncubationRun,
) -> IncubationRunPaths:
    """把一轮孵化运行记录写成标准 manifest。"""

    target_dir = output_dir / agent_key
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / f"{run_key}-run.json"
    manifest_path.write_text(
        json.dumps(serialize_incubation_run(run), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return IncubationRunPaths(target_dir=target_dir, manifest_path=manifest_path)


def load_incubation_run(path: Path) -> IncubationRun:
    """从标准 manifest 加载一轮孵化运行记录。"""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return deserialize_incubation_run(payload)


def serialize_incubation_run(run: IncubationRun) -> dict[str, object]:
    """序列化孵化运行记录。"""

    return {
        "agent_key": run.agent_key,
        "run_title": run.run_title,
        "stages": [_serialize_stage(stage) for stage in run.stages],
    }


def deserialize_incubation_run(payload: dict[str, object]) -> IncubationRun:
    """反序列化孵化运行记录。"""

    return IncubationRun(
        agent_key=str(payload["agent_key"]),
        run_title=str(payload["run_title"]),
        stages=[
            _deserialize_stage(stage_payload)
            for stage_payload in payload.get("stages", [])
        ],
    )


def _serialize_stage(stage: IncubationStageRecord) -> dict[str, object]:
    return {
        "stage": stage.stage.value,
        "status": stage.status,
        "notes": stage.notes,
        "outputs": list(stage.outputs),
        "sample_sets": [asdict(sample_set) for sample_set in stage.sample_sets],
        "comparisons": [asdict(comparison) for comparison in stage.comparisons],
        "recommendations": [
            asdict(recommendation) for recommendation in stage.recommendations
        ],
    }


def _deserialize_stage(payload: dict[str, object]) -> IncubationStageRecord:
    return IncubationStageRecord(
        stage=IncubationStage(str(payload["stage"])),
        status=str(payload.get("status", "pending")),
        notes=str(payload.get("notes", "")),
        outputs=list(payload.get("outputs", [])),
        sample_sets=[
            SampleSet(**sample_set) for sample_set in payload.get("sample_sets", [])
        ],
        comparisons=[
            ValidationComparison(**comparison)
            for comparison in payload.get("comparisons", [])
        ],
        recommendations=[
            DistillationRecommendation(**recommendation)
            for recommendation in payload.get("recommendations", [])
        ],
    )
