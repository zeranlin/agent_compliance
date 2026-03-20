from __future__ import annotations

import json
from http import HTTPStatus

from agent_compliance.incubator.improvement.rule_management import load_rule_management_payload, save_rule_decision


def rules_payload() -> dict:
    return load_rule_management_payload()


def handle_rule_decision(handler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        candidate_rule_id = str(payload.get("candidate_rule_id", "")).strip()
        decision = str(payload.get("decision", "")).strip()
        note = str(payload.get("note", "")).strip()
        if not candidate_rule_id:
            handler._send_json({"error": "缺少 candidate_rule_id"}, status=HTTPStatus.BAD_REQUEST)
            return
        save_rule_decision(candidate_rule_id, decision, note)
        handler._send_json(load_rule_management_payload())
    except Exception as exc:
        handler._send_json({"error": f"保存规则决策失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
