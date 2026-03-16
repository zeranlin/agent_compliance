from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_compliance.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.config import detect_paths
from agent_compliance.evals.runner import benchmark_summary
from agent_compliance.pipelines.normalize import run_normalize
from agent_compliance.pipelines.render import write_review_outputs
from agent_compliance.pipelines.review import build_review_result
from agent_compliance.pipelines.rule_scan import run_rule_scan
from agent_compliance.rules.base import RULE_SET_VERSION


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
    review_parser.add_argument("--refresh-cache", action="store_true")

    eval_parser = subparsers.add_parser("eval", help="Show benchmark entry points")
    eval_parser.add_argument("--json", action="store_true")

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
        reference_snapshot = reference_snapshot_id(paths.repo_root / "docs" / "references")
        cache_key = build_review_cache_key(
            file_hash=normalized.file_hash,
            rule_set_version=RULE_SET_VERSION,
            reference_snapshot=reference_snapshot,
            review_pipeline_version=REVIEW_CACHE_VERSION,
        )
        review = None
        cache_used = False
        if not args.refresh_cache:
            review = load_review_cache(cache_key)
            cache_used = review is not None
        if review is None:
            hits = run_rule_scan(normalized)
            review = build_review_result(normalized, hits)
            save_review_cache(
                cache_key,
                review,
                metadata={
                    "file_hash": normalized.file_hash,
                    "rule_set_version": RULE_SET_VERSION,
                    "reference_snapshot": reference_snapshot,
                    "review_pipeline_version": REVIEW_CACHE_VERSION,
                },
            )
        output_stem = args.output_stem or normalized.file_hash[:12]
        json_path, md_path = write_review_outputs(review, output_stem)
        payload = {
            "review": review.to_dict(),
            "cache": {"used": cache_used, "key": cache_key},
            "outputs": {"json": str(json_path), "markdown": str(md_path)},
        }
        return _print_result(payload, args.json)

    if args.command == "eval":
        return _print_result(benchmark_summary(), args.json)

    parser.error("Unknown command")
    return 2


def _print_result(payload: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0
