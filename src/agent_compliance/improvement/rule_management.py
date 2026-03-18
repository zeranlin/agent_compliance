from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_compliance.config import detect_paths
from agent_compliance.knowledge.rule_registry import build_rule_registry


DECISIONS_FILE = "rule-decisions.json"


def load_rule_management_payload() -> dict[str, Any]:
    paths = detect_paths()
    decisions = _load_decisions(paths.improvement_root / DECISIONS_FILE)
    candidates = _load_candidates(paths.improvement_root, decisions)
    formal_rules = _load_formal_rules()
    return {
        "formal_rules": formal_rules,
        "candidate_rules": candidates,
        "decision_summary": _decision_summary(candidates),
        "formal_rule_summary": _formal_rule_summary(formal_rules),
        "catalog_scene_summary": _catalog_scene_summary(candidates),
        "domain_summary": _domain_summary(candidates),
        "authority_summary": _authority_summary(candidates),
        "decisions_path": str(paths.improvement_root / DECISIONS_FILE),
    }


def save_rule_decision(candidate_rule_id: str, decision: str, note: str = "") -> dict[str, Any]:
    if decision not in {"confirmed", "deferred", "ignored"}:
        raise ValueError("不支持的规则决策状态")
    paths = detect_paths()
    path = paths.improvement_root / DECISIONS_FILE
    data = _load_decisions(path)
    data[candidate_rule_id] = {"decision": decision, "note": note}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data[candidate_rule_id]


def _load_candidates(root: Path, decisions: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    gate_by_id: dict[str, dict[str, Any]] = {}
    for gate_path in sorted(root.glob("*-benchmark-gate.json")):
        try:
            payload = json.loads(gate_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in payload.get("results", []):
            if isinstance(item, dict) and item.get("candidate_rule_id"):
                gate_by_id[str(item["candidate_rule_id"])] = item
    for candidate_path in sorted(root.glob("*-rule-candidates.json")):
        try:
            payload = json.loads(candidate_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, list):
            continue
        stem = candidate_path.name.removesuffix("-rule-candidates.json")
        for item in payload:
            if not isinstance(item, dict) or not item.get("candidate_rule_id"):
                continue
            candidate_rule_id = str(item["candidate_rule_id"])
            decision_record = decisions.get(candidate_rule_id, {})
            gate_record = gate_by_id.get(candidate_rule_id, {})
            candidates.append(
                {
                    **item,
                    "output_stem": stem,
                    "decision": decision_record.get("decision", "pending"),
                    "decision_note": decision_record.get("note", ""),
                    "gate_status": gate_record.get("status", "unknown"),
                    "gate_reason": gate_record.get("reason", "尚未找到对应 benchmark gate 结果。"),
                }
            )
    candidates.sort(key=lambda item: (item["decision"] != "pending", item["candidate_rule_id"]))
    return candidates


def _load_decisions(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_formal_rules() -> list[dict[str, Any]]:
    items = [
        {
            "rule_id": entry.rule_id,
            "issue_type": entry.issue_type,
            "source_section": entry.source_section,
            "merge_key": entry.merge_key,
            "rule_family": entry.rule_family,
            "governance_tier": entry.governance_tier,
            "rule_status": entry.rule_status,
            "enabled_by_default": entry.enabled_by_default,
            "default_priority": entry.default_priority,
            "related_reference_ids": list(entry.related_reference_ids),
        }
        for entry in build_rule_registry()
    ]
    items.sort(key=lambda item: (item["rule_family"], item["rule_id"]))
    return items


def _decision_summary(candidates: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"pending": 0, "confirmed": 0, "deferred": 0, "ignored": 0}
    for item in candidates:
        decision = str(item.get("decision", "pending"))
        summary[decision] = summary.get(decision, 0) + 1
    summary["total"] = len(candidates)
    return summary


def _formal_rule_summary(formal_rules: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for item in formal_rules:
        by_status[item["rule_status"]] = by_status.get(item["rule_status"], 0) + 1
        by_tier[item["governance_tier"]] = by_tier.get(item["governance_tier"], 0) + 1
        by_family[item["rule_family"]] = by_family.get(item["rule_family"], 0) + 1
    return {
        "total": len(formal_rules),
        "by_status": by_status,
        "by_tier": by_tier,
        "by_family": by_family,
    }


def _catalog_scene_summary(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in candidates:
        key = str(item.get("primary_catalog_name") or "").strip()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [
        {"primary_catalog_name": key, "candidate_count": count}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _domain_summary(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in candidates:
        key = str(item.get("primary_domain_key") or "").strip()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [
        {"primary_domain_key": key, "candidate_count": count}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _authority_summary(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in candidates:
        key = str(item.get("primary_authority") or "").strip()
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return [
        {"primary_authority": key, "candidate_count": count}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
