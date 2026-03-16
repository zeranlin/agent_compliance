from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    generated_root: Path
    normalized_root: Path
    review_root: Path
    cache_root: Path


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool
    base_url: str
    model: str
    timeout_seconds: int


def detect_paths() -> AppPaths:
    repo_root = Path(__file__).resolve().parents[2]
    generated_root = repo_root / "docs" / "generated"
    return AppPaths(
        repo_root=repo_root,
        generated_root=generated_root,
        normalized_root=generated_root / "normalized-documents",
        review_root=generated_root / "reviews",
        cache_root=generated_root / "cache",
    )


def detect_llm_config() -> LLMConfig:
    return LLMConfig(
        enabled=_env_flag("AGENT_COMPLIANCE_LLM_ENABLED", default=False),
        base_url=os.getenv("AGENT_COMPLIANCE_LLM_BASE_URL", "http://112.111.54.86:10011/v1").rstrip("/"),
        model=os.getenv("AGENT_COMPLIANCE_LLM_MODEL", "local-model"),
        timeout_seconds=int(os.getenv("AGENT_COMPLIANCE_LLM_TIMEOUT_SECONDS", "60")),
    )


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
