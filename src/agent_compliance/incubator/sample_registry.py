from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from agent_compliance.incubator.lifecycle import SampleSet


@dataclass(frozen=True)
class SampleAsset:
    """描述一条可用于孵化或蒸馏的样例资产。"""

    sample_id: str
    label: str
    path: str
    notes: str = ""


@dataclass(frozen=True)
class SampleManifest:
    """描述一批样例资产的登记结果。"""

    name: str
    assets: tuple[SampleAsset, ...]
    version: str = "v1"
    agent_key: str = ""
    benchmark_refs: tuple[str, ...] = ()
    change_summary: str = ""

    @property
    def positive_examples(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets if asset.label == "positive")

    @property
    def negative_examples(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets if asset.label == "negative")

    @property
    def boundary_examples(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets if asset.label == "boundary")

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets)

    def to_sample_set(self, *, benchmark_refs: tuple[str, ...] = ()) -> SampleSet:
        """把样例清单转成孵化闭环使用的 `SampleSet`。"""

        merged_benchmark_refs = tuple(
            dict.fromkeys(self.benchmark_refs + tuple(benchmark_refs))
        )
        return SampleSet(
            name=f"{self.name}@{self.version}",
            positive_examples=self.positive_examples,
            negative_examples=self.negative_examples,
            boundary_examples=self.boundary_examples,
            benchmark_refs=merged_benchmark_refs,
        )


def build_sample_manifest(
    name: str,
    *,
    positive_paths: tuple[str, ...] = (),
    negative_paths: tuple[str, ...] = (),
    boundary_paths: tuple[str, ...] = (),
    version: str = "v1",
    agent_key: str = "",
    benchmark_refs: tuple[str, ...] = (),
    change_summary: str = "",
) -> SampleManifest:
    """根据路径集合生成标准化样例清单。"""

    assets: list[SampleAsset] = []
    assets.extend(_build_assets("positive", positive_paths))
    assets.extend(_build_assets("negative", negative_paths))
    assets.extend(_build_assets("boundary", boundary_paths))
    return SampleManifest(
        name=name,
        assets=tuple(assets),
        version=version,
        agent_key=agent_key,
        benchmark_refs=benchmark_refs,
        change_summary=change_summary,
    )


def write_sample_manifest(output_dir: Path, manifest: SampleManifest) -> Path:
    """把样例清单写成标准化 JSON 资产。"""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"{manifest.name}-{manifest.version}-sample-manifest.json"
    manifest_path.write_text(
        json.dumps(serialize_sample_manifest(manifest), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


def load_sample_manifest(path: Path) -> SampleManifest:
    """从标准 JSON 资产加载样例清单。"""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return deserialize_sample_manifest(payload)


def serialize_sample_manifest(manifest: SampleManifest) -> dict[str, object]:
    """序列化样例清单。"""

    return {
        "name": manifest.name,
        "version": manifest.version,
        "agent_key": manifest.agent_key,
        "benchmark_refs": list(manifest.benchmark_refs),
        "change_summary": manifest.change_summary,
        "assets": [asdict(asset) for asset in manifest.assets],
    }


def deserialize_sample_manifest(payload: dict[str, object]) -> SampleManifest:
    """反序列化样例清单。"""

    return SampleManifest(
        name=str(payload["name"]),
        version=str(payload.get("version", "v1")),
        agent_key=str(payload.get("agent_key", "")),
        benchmark_refs=tuple(payload.get("benchmark_refs", [])),
        change_summary=str(payload.get("change_summary", "")),
        assets=tuple(
            SampleAsset(**asset)
            for asset in payload.get("assets", [])
        ),
    )


def summarize_sample_manifest(manifest: SampleManifest) -> dict[str, object]:
    """生成样例清单摘要。"""

    return {
        "name": manifest.name,
        "version": manifest.version,
        "agent_key": manifest.agent_key,
        "total_assets": len(manifest.assets),
        "positive_count": len(manifest.positive_examples),
        "negative_count": len(manifest.negative_examples),
        "boundary_count": len(manifest.boundary_examples),
        "sample_ids": tuple(asset.sample_id for asset in manifest.assets),
        "benchmark_refs": manifest.benchmark_refs,
        "change_summary": manifest.change_summary,
    }


def _build_assets(label: str, paths: tuple[str, ...]) -> list[SampleAsset]:
    assets = []
    for path in paths:
        sample_id = Path(path).stem
        assets.append(SampleAsset(sample_id=sample_id, label=label, path=path))
    return assets
