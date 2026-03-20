from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from agent_compliance.core.cache.review_cache import (
    REVIEW_CACHE_VERSION,
    build_review_cache_key,
    load_review_cache,
    reference_snapshot_id,
    save_review_cache,
)
from agent_compliance.core.config import LLMConfig, detect_llm_config, detect_paths, detect_tender_parser_mode
from agent_compliance.incubator import (
    IncubationStage,
    ValidationComparison,
    bootstrap_agent_factory,
    build_regression_feedback,
    build_sample_manifest,
    build_run_comparison_report,
    build_validation_comparison_from_files,
    load_incubation_run,
    render_run_comparison_markdown,
    resume_agent_factory,
    write_incubation_run,
    write_distillation_report,
)
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

    incubate_parser = subparsers.add_parser(
        "incubate-agent",
        help="Bootstrap a new agent incubation run from a standard blueprint",
    )
    incubate_parser.add_argument("agent_key")
    incubate_parser.add_argument(
        "--agents-dir",
        type=Path,
        default=Path("src/agent_compliance/agents"),
    )
    incubate_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/generated/incubator"),
    )
    incubate_parser.add_argument("--run-title", default=None)
    incubate_parser.add_argument(
        "--resume-run",
        type=Path,
        default=None,
        help="Resume an existing incubation run manifest",
    )
    incubate_parser.add_argument("--overwrite", action="store_true")
    incubate_parser.add_argument(
        "--positive-sample",
        action="append",
        default=[],
        help="Add a positive sample path",
    )
    incubate_parser.add_argument(
        "--negative-sample",
        action="append",
        default=[],
        help="Add a negative sample path",
    )
    incubate_parser.add_argument(
        "--boundary-sample",
        action="append",
        default=[],
        help="Add a boundary sample path",
    )
    incubate_parser.add_argument(
        "--comparisons-json",
        type=Path,
        default=None,
        help="Path to a JSON file containing ValidationComparison items",
    )
    incubate_parser.add_argument("--sample-id", default=None)
    incubate_parser.add_argument("--human-baseline-file", type=Path, default=None)
    incubate_parser.add_argument("--strong-agent-result-file", type=Path, default=None)
    incubate_parser.add_argument("--target-agent-result-file", type=Path, default=None)
    incubate_parser.add_argument("--comparison-summary", default="")
    incubate_parser.add_argument("--json", action="store_true")

    compare_runs_parser = subparsers.add_parser(
        "compare-incubation-runs",
        help="Compare multiple incubation run manifests for the same agent",
    )
    compare_runs_parser.add_argument("run_manifests", nargs="+", type=Path)
    compare_runs_parser.add_argument("--json", action="store_true")

    update_recommendation_parser = subparsers.add_parser(
        "update-incubation-recommendation",
        help="Update recommendation execution status in a run manifest",
    )
    update_recommendation_parser.add_argument("run_manifest", type=Path)
    update_recommendation_parser.add_argument("recommendation_key")
    update_recommendation_parser.add_argument(
        "--stage",
        choices=[stage.value for stage in IncubationStage],
        default=IncubationStage.DISTILLATION_ITERATION.value,
    )
    update_recommendation_parser.add_argument(
        "--status",
        required=True,
        choices=("proposed", "accepted", "implemented", "validated", "dropped"),
    )
    update_recommendation_parser.add_argument("--notes", default="")
    update_recommendation_parser.add_argument("--regression-result", default="")
    update_recommendation_parser.add_argument("--capability-change", default="")
    update_recommendation_parser.add_argument("--sample-id", default=None)
    update_recommendation_parser.add_argument("--human-baseline-file", type=Path, default=None)
    update_recommendation_parser.add_argument("--strong-agent-result-file", type=Path, default=None)
    update_recommendation_parser.add_argument("--target-agent-result-file", type=Path, default=None)
    update_recommendation_parser.add_argument("--comparison-summary", default="")
    update_recommendation_parser.add_argument("--json", action="store_true")

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

    if args.command == "incubate-agent":
        sample_manifest = None
        if args.positive_sample or args.negative_sample or args.boundary_sample:
            sample_manifest = build_sample_manifest(
                name=f"{args.agent_key}-samples",
                positive_paths=tuple(args.positive_sample),
                negative_paths=tuple(args.negative_sample),
                boundary_paths=tuple(args.boundary_sample),
            )
        comparisons = _load_comparisons(args.comparisons_json)
        auto_comparison = _build_auto_comparison(args)
        if auto_comparison is not None:
            comparisons = comparisons + (auto_comparison,)
        if args.resume_run is not None:
            run = load_incubation_run(args.resume_run)
            if run.agent_key != args.agent_key:
                raise ValueError(
                    f"resume run agent_key={run.agent_key} does not match requested {args.agent_key}"
                )
            result = resume_agent_factory(
                run,
                sample_manifest=sample_manifest,
                comparisons=comparisons,
            )
            run_key = _run_key_from_manifest(args.resume_run)
        else:
            result = bootstrap_agent_factory(
                args.agents_dir,
                args.agent_key,
                run_title=args.run_title,
                sample_manifest=sample_manifest,
                comparisons=comparisons,
                overwrite=args.overwrite,
            )
            run_key = _slugify_run_key(result.run.run_title)
        artifact_paths = write_distillation_report(
            args.output_dir,
            result.blueprint.agent_key,
            run_key,
            result.report,
            result.report_markdown,
        )
        run_paths = write_incubation_run(
            args.output_dir,
            result.blueprint.agent_key,
            run_key,
            result.run,
        )
        payload = {
            "agent_key": result.blueprint.agent_key,
            "agent_name": result.blueprint.agent_name,
            "scaffold_root": (
                str(result.scaffold_plan.target_root)
                if result.scaffold_plan is not None
                else None
            ),
            "completed_stages": result.report["summary"]["completed_stages"],
            "recommendation_count": result.report["summary"]["recommendation_count"],
            "outputs": {
                "run_manifest": str(run_paths.manifest_path),
                "json": str(artifact_paths.json_path),
                "markdown": str(artifact_paths.markdown_path),
            },
        }
        return _print_result(payload, args.json)

    if args.command == "compare-incubation-runs":
        runs = tuple(load_incubation_run(path) for path in args.run_manifests)
        report = build_run_comparison_report(runs)
        if args.json:
            return _print_result(report, True)
        print(render_run_comparison_markdown(report))
        return 0

    if args.command == "update-incubation-recommendation":
        run = load_incubation_run(args.run_manifest)
        stage = IncubationStage(args.stage)
        regression_result = args.regression_result
        capability_change = args.capability_change
        auto_comparison = _build_auto_comparison(args)
        if auto_comparison is not None:
            previous_comparison = run.latest_comparison(
                IncubationStage.PARITY_VALIDATION,
                auto_comparison.sample_id,
            )
            feedback = build_regression_feedback(previous_comparison, auto_comparison)
            run.add_comparison(IncubationStage.PARITY_VALIDATION, auto_comparison)
            run.set_stage_status(
                IncubationStage.PARITY_VALIDATION,
                "completed",
                f"已补充样例 {auto_comparison.sample_id} 的回归对照。",
            )
            regression_result = regression_result or feedback.regression_result
            capability_change = capability_change or feedback.capability_change
        run.update_recommendation_status(
            stage,
            args.recommendation_key,
            args.status,
            args.notes,
            regression_result,
            capability_change,
        )
        write_incubation_run(
            args.run_manifest.parent.parent,
            run.agent_key,
            _run_key_from_manifest(args.run_manifest),
            run,
        )
        payload = {
            "agent_key": run.agent_key,
            "run_manifest": str(args.run_manifest),
            "recommendation_key": args.recommendation_key,
            "stage": stage.value,
            "status": args.status,
            "notes": args.notes,
            "regression_result": regression_result,
            "capability_change": capability_change,
            "auto_comparison_added": auto_comparison is not None,
        }
        return _print_result(payload, args.json)

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


def _load_comparisons(path: Path | None) -> tuple[ValidationComparison, ...]:
    if path is None:
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("comparisons JSON must be a list")
    comparisons: list[ValidationComparison] = []
    for item in payload:
        comparisons.append(
            ValidationComparison(
                sample_id=item["sample_id"],
                human_baseline=item["human_baseline"],
                strong_agent_result=item["strong_agent_result"],
                target_agent_result=item["target_agent_result"],
                aligned_points=tuple(item.get("aligned_points", [])),
                gap_points=tuple(item.get("gap_points", [])),
                summary=item.get("summary", ""),
            )
        )
    return tuple(comparisons)


def _build_auto_comparison(args: argparse.Namespace) -> ValidationComparison | None:
    files = (
        args.human_baseline_file,
        args.strong_agent_result_file,
        args.target_agent_result_file,
    )
    if not any(files):
        return None
    if not all(files):
        raise ValueError(
            "human-baseline-file, strong-agent-result-file and target-agent-result-file must be provided together"
        )
    agent_key = getattr(args, "agent_key", "agent")
    sample_id = args.sample_id or f"{agent_key}-auto-001"
    return build_validation_comparison_from_files(
        sample_id=sample_id,
        human_baseline_path=args.human_baseline_file,
        strong_agent_result_path=args.strong_agent_result_file,
        target_agent_result_path=args.target_agent_result_file,
        summary=args.comparison_summary or "",
    )


def _slugify_run_key(run_title: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    normalized = "".join(char if char.isalnum() else "-" for char in run_title.lower())
    normalized = "-".join(part for part in normalized.split("-") if part)
    return f"{timestamp}-{normalized or 'incubation-run'}"


def _run_key_from_manifest(path: Path) -> str:
    suffix = "-run.json"
    name = path.name
    return name[: -len(suffix)] if name.endswith(suffix) else path.stem
