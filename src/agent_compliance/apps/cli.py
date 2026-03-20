from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_compliance.core.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.core.config import LLMConfig, detect_llm_config, detect_paths, detect_tender_parser_mode
from agent_compliance.incubator.evals.runner import benchmark_summary
from agent_compliance.agents.compliance_review.pipelines.llm_enhance import enhance_review_result
from agent_compliance.agents.compliance_review.pipelines.llm_review import apply_llm_review_tasks
from agent_compliance.core.pipelines.normalize import run_normalize
from agent_compliance.agents.compliance_review.pipelines.render import write_review_outputs
from agent_compliance.agents.compliance_review.pipelines.review import build_review_result
from agent_compliance.agents.compliance_review.pipelines.rule_scan import run_rule_scan
from agent_compliance.agents.compliance_review.rules.base import RULE_SET_VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-compliance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser("normalize", help="Normalize a procurement file into local artifacts")
    normalize_parser.add_argument("file", type=Path)
    normalize_parser.add_argument("--json", action="store_true")

    scan_parser = subparsers.add_parser("scan-rules", help="Run deterministic rule scan on a file")
    scan_parser.add_argument("file", type=Path)
    scan_parser.add_argument("--json", action="store_true")

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

    eval_parser = subparsers.add_parser("eval", help="Show benchmark entry points")
    eval_parser.add_argument("--json", action="store_true")

    web_parser = subparsers.add_parser(
        "web",
        help="Run local review web UI",
        description="Run local review web UI",
    )
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8765)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "normalize":
        normalized = run_normalize(args.file)
        return _print_result(normalized.to_dict(), args.json)

    if args.command == "scan-rules":
        normalized = run_normalize(args.file)
        hits = run_rule_scan(normalized)
        return _print_result({"rule_hits": [hit.to_dict() for hit in hits]}, args.json)

    if args.command == "review":
        paths = detect_paths()
        normalized = run_normalize(args.file)
        llm_config = _resolved_llm_config(args)
        parser_mode = args.tender_parser_mode or detect_tender_parser_mode()
        reference_snapshot = reference_snapshot_id(paths.repo_root / "docs" / "references")
        cache_key = build_review_cache_key(
            file_hash=normalized.file_hash,
            rule_set_version=RULE_SET_VERSION,
            reference_snapshot=reference_snapshot,
            parser_mode=parser_mode,
            review_pipeline_version=REVIEW_CACHE_VERSION,
        )
        review = None
        cache_used = False
        cache_enabled = args.use_cache
        if cache_enabled and not args.refresh_cache:
            review = load_review_cache(cache_key)
            cache_used = review is not None
        if review is None:
            hits = run_rule_scan(normalized)
            review = build_review_result(normalized, hits, parser_mode=parser_mode)
            if cache_enabled:
                save_review_cache(
                    cache_key,
                    review,
                    metadata={
                        "file_hash": normalized.file_hash,
                        "rule_set_version": RULE_SET_VERSION,
                        "reference_snapshot": reference_snapshot,
                        "parser_mode": parser_mode,
                        "review_pipeline_version": REVIEW_CACHE_VERSION,
                    },
                )
        output_stem = args.output_stem or normalized.file_hash[:12]
        review = enhance_review_result(review, llm_config)
        review, llm_artifacts = apply_llm_review_tasks(
            normalized,
            review,
            llm_config,
            output_stem=output_stem,
        )
        json_path, md_path = write_review_outputs(review, output_stem)
        payload = {
            "review": review.to_dict(),
            "cache": {"enabled": cache_enabled, "used": cache_used, "key": cache_key},
            "llm": {
                "enabled": llm_config.enabled,
                "base_url": llm_config.base_url,
                "model": llm_config.model,
            },
            "parser": {"mode": parser_mode, "enabled": parser_mode != "off"},
            "llm_review": llm_artifacts.to_dict(),
            "outputs": {"json": str(json_path), "markdown": str(md_path)},
        }
        return _print_result(payload, args.json)

    if args.command == "eval":
        return _print_result(benchmark_summary(), args.json)

    if args.command == "web":
        from agent_compliance.apps.web.app import run_web_server

        run_web_server(host=args.host, port=args.port)
        return 0

    parser.error("Unknown command")
    return 2


def _print_result(payload: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0


def _resolved_llm_config(args) -> LLMConfig:
    config = detect_llm_config()
    return LLMConfig(
        enabled=bool(args.use_llm or config.enabled),
        base_url=(args.llm_base_url or config.base_url).rstrip("/"),
        model=args.llm_model or config.model,
        api_key=config.api_key,
        timeout_seconds=config.timeout_seconds,
    )
