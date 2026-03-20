from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VALID_TENDER_PARSER_MODES = {"off", "assist", "required"}


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    generated_root: Path
    normalized_root: Path
    review_root: Path
    cache_root: Path
    uploads_root: Path
    improvement_root: Path


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool
    base_url: str
    model: str
    api_key: str | None
    timeout_seconds: int


def detect_paths() -> AppPaths:
    repo_root = Path(__file__).resolve().parents[3]
    generated_root = repo_root / "docs" / "generated"
    return AppPaths(
        repo_root=repo_root,
        generated_root=generated_root,
        normalized_root=generated_root / "normalized-documents",
        review_root=generated_root / "reviews",
        cache_root=generated_root / "cache",
        uploads_root=generated_root / "uploads",
        improvement_root=generated_root / "improvement",
    )


def detect_llm_config() -> LLMConfig:
    _load_local_env()
    return LLMConfig(
        enabled=_env_flag("AGENT_COMPLIANCE_LLM_ENABLED", default=False),
        base_url=os.getenv("AGENT_COMPLIANCE_LLM_BASE_URL", "http://112.111.54.86:10011/v1").rstrip("/"),
        model=os.getenv("AGENT_COMPLIANCE_LLM_MODEL", "qwen3.5-27b"),
        api_key=os.getenv("AGENT_COMPLIANCE_LLM_API_KEY"),
        timeout_seconds=int(os.getenv("AGENT_COMPLIANCE_LLM_TIMEOUT_SECONDS", "60")),
    )


def detect_tender_parser_mode(default: str = "off") -> str:
    _load_local_env()
    value = (os.getenv("AGENT_COMPLIANCE_TENDER_PARSER_MODE") or default).strip().lower()
    if value not in VALID_TENDER_PARSER_MODES:
        return default
    return value


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_local_env() -> None:
    env_path = detect_paths().repo_root / ".env.local"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
