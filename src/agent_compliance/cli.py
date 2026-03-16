from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_compliance.evals.runner import benchmark_summary
from agent_compliance.pipelines.normalize import run_normalize
from agent_compliance.pipelines.render import write_review_outputs
from agent_compliance.pipelines.review import build_review_result
from agent_compliance.pipelines.rule_scan import run_rule_scan


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
        normalized = run_normalize(args.file)
        hits = run_rule_scan(normalized)
        review = build_review_result(normalized, hits)
        output_stem = args.output_stem or normalized.file_hash[:12]
        json_path, md_path = write_review_outputs(review, output_stem)
        payload = {
            "review": review.to_dict(),
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
