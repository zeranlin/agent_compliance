from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from agent_compliance.incubator import (
    IncubationStage,
    ValidationComparison,
    bootstrap_agent_factory,
    build_productization_package,
    build_regression_feedback,
    build_run_comparison_report,
    build_sample_manifest,
    build_validation_comparison_from_files,
    collect_validation_comparisons_from_manifest,
    collect_validation_comparisons_from_root,
    load_incubation_run,
    load_sample_manifest,
    render_productization_markdown,
    render_run_comparison_markdown,
    resume_agent_factory,
    write_distillation_report,
    write_incubation_run,
    write_productization_package,
    write_sample_manifest,
)


def register_incubator_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    handlers: dict[str, Callable[[argparse.Namespace], int]],
) -> None:
    incubate_parser = subparsers.add_parser(
        "incubate-agent",
        help="Bootstrap a new agent incubation run from a standard blueprint",
    )
    incubate_parser.add_argument("agent_key")
    incubate_parser.add_argument("--agents-dir", type=Path, default=Path("src/agent_compliance/agents"))
    incubate_parser.add_argument("--output-dir", type=Path, default=Path("docs/generated/incubator"))
    incubate_parser.add_argument("--run-title", default=None)
    incubate_parser.add_argument("--resume-run", type=Path, default=None, help="Resume an existing incubation run manifest")
    incubate_parser.add_argument("--overwrite", action="store_true")
    incubate_parser.add_argument("--positive-sample", action="append", default=[], help="Add a positive sample path")
    incubate_parser.add_argument("--negative-sample", action="append", default=[], help="Add a negative sample path")
    incubate_parser.add_argument("--boundary-sample", action="append", default=[], help="Add a boundary sample path")
    incubate_parser.add_argument("--sample-manifest-version", default="v1")
    incubate_parser.add_argument("--sample-change-summary", default="")
    incubate_parser.add_argument("--sample-manifest-file", type=Path, default=None, help="Load a pre-versioned sample manifest JSON")
    incubate_parser.add_argument("--comparisons-json", type=Path, default=None, help="Path to a JSON file containing ValidationComparison items")
    incubate_parser.add_argument("--comparison-root", type=Path, default=None, help="Root directory containing standard comparison subfolders")
    incubate_parser.add_argument("--sample-id", default=None)
    incubate_parser.add_argument("--human-baseline-file", type=Path, default=None)
    incubate_parser.add_argument("--strong-agent-result-file", type=Path, default=None)
    incubate_parser.add_argument("--target-agent-result-file", type=Path, default=None)
    incubate_parser.add_argument("--comparison-summary", default="")
    incubate_parser.add_argument("--json", action="store_true")
    handlers["incubate-agent"] = handle_incubate_agent

    compare_runs_parser = subparsers.add_parser(
        "compare-incubation-runs",
        help="Compare multiple incubation run manifests for the same agent",
    )
    compare_runs_parser.add_argument("run_manifests", nargs="+", type=Path)
    compare_runs_parser.add_argument("--json", action="store_true")
    handlers["compare-incubation-runs"] = handle_compare_incubation_runs

    productize_parser = subparsers.add_parser(
        "productize-incubation-run",
        help="Generate productization templates from an incubation run manifest",
    )
    productize_parser.add_argument("run_manifest", type=Path)
    productize_parser.add_argument("--output-dir", type=Path, default=Path("docs/generated/incubator-productization"))
    productize_parser.add_argument("--json", action="store_true")
    handlers["productize-incubation-run"] = handle_productize_incubation_run

    update_parser = subparsers.add_parser(
        "update-incubation-recommendation",
        help="Update recommendation execution status in a run manifest",
    )
    update_parser.add_argument("run_manifest", type=Path)
    update_parser.add_argument("recommendation_key")
    update_parser.add_argument("--stage", choices=[stage.value for stage in IncubationStage], default=IncubationStage.DISTILLATION_ITERATION.value)
    update_parser.add_argument("--status", required=True, choices=("proposed", "accepted", "implemented", "validated", "dropped"))
    update_parser.add_argument("--notes", default="")
    update_parser.add_argument("--regression-result", default="")
    update_parser.add_argument("--capability-change", default="")
    update_parser.add_argument("--sample-id", default=None)
    update_parser.add_argument("--comparison-root", type=Path, default=None)
    update_parser.add_argument("--human-baseline-file", type=Path, default=None)
    update_parser.add_argument("--strong-agent-result-file", type=Path, default=None)
    update_parser.add_argument("--target-agent-result-file", type=Path, default=None)
    update_parser.add_argument("--comparison-summary", default="")
    update_parser.add_argument("--json", action="store_true")
    handlers["update-incubation-recommendation"] = handle_update_incubation_recommendation


def handle_incubate_agent(args: argparse.Namespace) -> int:
    sample_manifest = _resolve_sample_manifest(args)
    comparisons = _load_comparisons(args.comparisons_json)
    comparisons = comparisons + _collect_comparisons(args, sample_manifest)
    auto_comparison = _build_auto_comparison(args)
    if auto_comparison is not None:
        comparisons = comparisons + (auto_comparison,)

    if args.resume_run is not None:
        run = load_incubation_run(args.resume_run)
        if run.agent_key != args.agent_key:
            raise ValueError(f"resume run agent_key={run.agent_key} does not match requested {args.agent_key}")
        result = resume_agent_factory(run, sample_manifest=sample_manifest, comparisons=comparisons)
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

    artifact_paths = write_distillation_report(args.output_dir, result.blueprint.agent_key, run_key, result.report, result.report_markdown)
    run_paths = write_incubation_run(args.output_dir, result.blueprint.agent_key, run_key, result.run)
    sample_manifest_path = None
    if sample_manifest is not None:
        sample_manifest_path = write_sample_manifest(args.output_dir / result.blueprint.agent_key / "sample-assets", sample_manifest)
    payload = {
        "agent_key": result.blueprint.agent_key,
        "agent_name": result.blueprint.agent_name,
        "scaffold_root": str(result.scaffold_plan.target_root) if result.scaffold_plan is not None else None,
        "completed_stages": result.report["summary"]["completed_stages"],
        "recommendation_count": result.report["summary"]["recommendation_count"],
        "outputs": {
            "run_manifest": str(run_paths.manifest_path),
            "json": str(artifact_paths.json_path),
            "markdown": str(artifact_paths.markdown_path),
            "sample_manifest": str(sample_manifest_path) if sample_manifest_path else None,
        },
    }
    return _print_result(payload, args.json)


def handle_compare_incubation_runs(args: argparse.Namespace) -> int:
    runs = tuple(load_incubation_run(path) for path in args.run_manifests)
    report = build_run_comparison_report(runs)
    if args.json:
        return _print_result(report, True)
    print(render_run_comparison_markdown(report))
    return 0


def handle_productize_incubation_run(args: argparse.Namespace) -> int:
    run = load_incubation_run(args.run_manifest)
    package = build_productization_package(run)
    markdown = render_productization_markdown(package)
    run_key = _run_key_from_manifest(args.run_manifest)
    artifact_paths = write_productization_package(args.output_dir, run.agent_key, run_key, package, markdown)
    run.set_stage_status(IncubationStage.PRODUCTIZATION, "completed", f"已生成产品化固化模板：{artifact_paths.markdown_path}")
    run.add_stage_output(IncubationStage.PRODUCTIZATION, str(artifact_paths.markdown_path))
    write_incubation_run(args.run_manifest.parent.parent, run.agent_key, run_key, run)
    payload = {
        "agent_key": run.agent_key,
        "run_manifest": str(args.run_manifest),
        "readiness_level": package["readiness_level"],
        "outputs": {"json": str(artifact_paths.json_path), "markdown": str(artifact_paths.markdown_path)},
    }
    return _print_result(payload, args.json)


def handle_update_incubation_recommendation(args: argparse.Namespace) -> int:
    run = load_incubation_run(args.run_manifest)
    stage = IncubationStage(args.stage)
    regression_result = args.regression_result
    capability_change = args.capability_change
    collected_comparisons = _collect_comparisons(args)
    auto_comparison = _build_auto_comparison(args)
    selected_comparison = None
    if collected_comparisons:
        if args.sample_id:
            for comparison in collected_comparisons:
                if comparison.sample_id == args.sample_id:
                    selected_comparison = comparison
                    break
        if selected_comparison is None:
            selected_comparison = collected_comparisons[0]
    auto_comparison = selected_comparison or auto_comparison
    if auto_comparison is not None:
        previous_comparison = run.latest_comparison(IncubationStage.PARITY_VALIDATION, auto_comparison.sample_id)
        feedback = build_regression_feedback(previous_comparison, auto_comparison)
        run.add_comparison(IncubationStage.PARITY_VALIDATION, auto_comparison)
        run.set_stage_status(IncubationStage.PARITY_VALIDATION, "completed", f"已补充样例 {auto_comparison.sample_id} 的回归对照。")
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
    write_incubation_run(args.run_manifest.parent.parent, run.agent_key, _run_key_from_manifest(args.run_manifest), run)
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


def _resolve_sample_manifest(args: argparse.Namespace):
    if args.sample_manifest_file is not None:
        return load_sample_manifest(args.sample_manifest_file)
    if args.positive_sample or args.negative_sample or args.boundary_sample:
        return build_sample_manifest(
            name=f"{args.agent_key}-samples",
            positive_paths=tuple(args.positive_sample),
            negative_paths=tuple(args.negative_sample),
            boundary_paths=tuple(args.boundary_sample),
            version=args.sample_manifest_version,
            agent_key=args.agent_key,
            change_summary=args.sample_change_summary,
        )
    return None


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
    files = (args.human_baseline_file, args.strong_agent_result_file, args.target_agent_result_file)
    if not any(files):
        return None
    if not all(files):
        raise ValueError("human/strong/target 三份对照文本必须同时提供")
    if not args.sample_id:
        raise ValueError("自动生成 comparison 时必须提供 --sample-id")
    return build_validation_comparison_from_files(
        sample_id=args.sample_id,
        human_baseline_path=args.human_baseline_file,
        strong_agent_result_path=args.strong_agent_result_file,
        target_agent_result_path=args.target_agent_result_file,
        summary=args.comparison_summary,
    )


def _collect_comparisons(args: argparse.Namespace, sample_manifest=None) -> tuple[ValidationComparison, ...]:
    comparisons: tuple[ValidationComparison, ...] = ()
    if args.comparison_root is not None:
        if sample_manifest is not None:
            comparisons = comparisons + collect_validation_comparisons_from_manifest(args.comparison_root, sample_manifest)
        else:
            comparisons = comparisons + collect_validation_comparisons_from_root(args.comparison_root)
    return comparisons


def _run_key_from_manifest(path: Path) -> str:
    name = path.name
    if name.endswith("-run.json"):
        return name[: -len("-run.json")]
    return path.stem


def _slugify_run_key(raw: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = "".join(ch if ch.isalnum() else "-" for ch in raw.strip().lower())
    slug = "-".join(part for part in slug.split("-") if part)
    if slug:
        return slug
    return f"{timestamp}-incubation-run"


def _print_result(payload: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0
