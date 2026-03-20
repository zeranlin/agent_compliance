from __future__ import annotations

from dataclasses import dataclass
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

    @property
    def positive_examples(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets if asset.label == "positive")

    @property
    def negative_examples(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets if asset.label == "negative")

    @property
    def boundary_examples(self) -> tuple[str, ...]:
        return tuple(asset.sample_id for asset in self.assets if asset.label == "boundary")

    def to_sample_set(self, *, benchmark_refs: tuple[str, ...] = ()) -> SampleSet:
        """把样例清单转成孵化闭环使用的 `SampleSet`。"""

        return SampleSet(
            name=self.name,
            positive_examples=self.positive_examples,
            negative_examples=self.negative_examples,
            boundary_examples=self.boundary_examples,
            benchmark_refs=benchmark_refs,
        )


def build_sample_manifest(
    name: str,
    *,
    positive_paths: tuple[str, ...] = (),
    negative_paths: tuple[str, ...] = (),
    boundary_paths: tuple[str, ...] = (),
) -> SampleManifest:
    """根据路径集合生成标准化样例清单。"""

    assets: list[SampleAsset] = []
    assets.extend(_build_assets("positive", positive_paths))
    assets.extend(_build_assets("negative", negative_paths))
    assets.extend(_build_assets("boundary", boundary_paths))
    return SampleManifest(name=name, assets=tuple(assets))


def summarize_sample_manifest(manifest: SampleManifest) -> dict[str, object]:
    """生成样例清单摘要。"""

    return {
        "name": manifest.name,
        "total_assets": len(manifest.assets),
        "positive_count": len(manifest.positive_examples),
        "negative_count": len(manifest.negative_examples),
        "boundary_count": len(manifest.boundary_examples),
        "sample_ids": tuple(asset.sample_id for asset in manifest.assets),
    }


def _build_assets(label: str, paths: tuple[str, ...]) -> list[SampleAsset]:
    assets = []
    for path in paths:
        sample_id = Path(path).stem
        assets.append(SampleAsset(sample_id=sample_id, label=label, path=path))
    return assets
