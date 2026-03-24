from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from agent_compliance.agents.compliance_review.pipeline import run_pipeline
from agent_compliance.core.config import LLMConfig, detect_llm_config
from agent_compliance.core.pipelines.normalize import run_normalize
from agent_compliance.agents.compliance_review.pipelines.rule_scan import run_rule_scan
from agent_compliance.incubator.evals.runner import benchmark_summary


def register_review_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    handlers: dict[str, Callable[[argparse.Namespace], int]],
) -> None:
    normalize_parser = subparsers.add_parser("normalize", help="Normalize a procurement file into local artifacts")
    normalize_parser.add_argument("file", type=Path)
    normalize_parser.add_argument("--json", action="store_true")
    handlers["normalize"] = handle_normalize

    scan_parser = subparsers.add_parser("scan-rules", help="Run deterministic rule scan on a file")
    scan_parser.add_argument("file", type=Path)
    scan_parser.add_argument("--json", action="store_true")
    handlers["scan-rules"] = handle_scan_rules

    review_parser = subparsers.add_parser("review", help="Run first-stage local review pipeline")
    review_parser.add_argument("file", type=Path)
    review_parser.add_argument("--json", action="store_true")
    review_parser.add_argument("--output-stem", default=None)
    review_parser.add_argument("--use-cache", action="store_true")
    review_parser.add_argument("--refresh-cache", action="store_true")
    review_parser.add_argument("--use-llm", action="store_true")
    review_parser.add_argument("--llm-base-url", default=None)
    review_parser.add_argument("--llm-model", default=None)
    review_parser.add_argument(
        "--tender-parser-mode",
        choices=("off", "assist", "required"),
        default=None,
        help="Configure whether to front-load the independent tender document parser",
    )
    handlers["review"] = handle_review

    eval_parser = subparsers.add_parser("eval", help="Show benchmark entry points")
    eval_parser.add_argument("--json", action="store_true")
    handlers["eval"] = handle_eval


def handle_normalize(args: argparse.Namespace) -> int:
    normalized = run_normalize(args.file)
    return _print_result(normalized.to_dict(), args.json)


def handle_scan_rules(args: argparse.Namespace) -> int:
    normalized = run_normalize(args.file)
    hits = run_rule_scan(normalized)
    return _print_result({"rule_hits": [hit.to_dict() for hit in hits]}, args.json)


def handle_review(args: argparse.Namespace) -> int:
    review_run = run_pipeline(
        args.file,
        use_cache=args.use_cache,
        refresh_cache=args.refresh_cache,
        llm_config=_resolved_llm_config(args),
        parser_mode=args.tender_parser_mode,
        output_stem=args.output_stem,
        write_outputs=True,
    )
    return _print_result(review_run.to_payload(), args.json)


def handle_eval(args: argparse.Namespace) -> int:
    return _print_result(benchmark_summary(), args.json)


def _resolved_llm_config(args: argparse.Namespace) -> LLMConfig:
    config = detect_llm_config()
    return LLMConfig(
        enabled=bool(args.use_llm or config.enabled),
        base_url=(args.llm_base_url or config.base_url).rstrip("/"),
        model=args.llm_model or config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )


def _print_result(payload: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0
