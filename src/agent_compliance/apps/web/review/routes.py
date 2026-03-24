from __future__ import annotations

import json
import subprocess
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs

from agent_compliance.agents.compliance_review.pipelines.review_export import export_review_bytes, write_export_output
from agent_compliance.apps.web.review.jobs import (
    create_review_job,
    review_job_result_payload,
    review_job_status_payload,
)
from agent_compliance.apps.web.review.service import (
    build_download_content_disposition,
    build_review_web_payload,
    flag_value,
    persist_upload,
    run_review_job,
    run_review_sync,
)
from agent_compliance.apps.web.shared.http import parse_multipart, send_json
from agent_compliance.core.config import detect_tender_parser_mode
from agent_compliance.core.schemas import ReviewResult


def handle_open_source(handler: BaseHTTPRequestHandler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        path = Path(payload.get("path", ""))
        if not path.exists():
            send_json(handler, {"error": "原文件不存在"}, status=HTTPStatus.BAD_REQUEST)
            return
        subprocess.run(["open", str(path)], check=True)
        send_json(handler, {"ok": True})
    except Exception as exc:
        send_json(handler, {"error": f"打开原文件失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def handle_export_review(handler: BaseHTTPRequestHandler) -> None:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
        review_payload = payload.get("review")
        if not isinstance(review_payload, dict):
            send_json(handler, {"error": "缺少 review 结果"}, status=HTTPStatus.BAD_REQUEST)
            return
        export_format = str(payload.get("format", "json")).strip().lower()
        mode = str(payload.get("mode", "summary")).strip().lower()
        review = ReviewResult.from_dict(review_payload)
        document_payload = payload.get("document") if isinstance(payload.get("document"), dict) else None
        stage_payload = payload.get("stage") if isinstance(payload.get("stage"), dict) else None
        if document_payload is not None and stage_payload:
            document_payload = {**document_payload, **stage_payload}
        content, content_type, filename = export_review_bytes(
            review,
            export_format=export_format,
            mode=mode,
            document_payload=document_payload,
        )
        write_export_output(review, export_format=export_format, mode=mode, document_payload=document_payload)
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Disposition", build_download_content_disposition(filename))
        handler.send_header("Content-Length", str(len(content)))
        handler.end_headers()
        handler.wfile.write(content)
    except Exception as exc:
        send_json(handler, {"error": f"导出失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)


def handle_review_start(handler: BaseHTTPRequestHandler) -> None:
    try:
        body = handler.rfile.read(int(handler.headers.get("Content-Length", "0")))
        fields = parse_multipart(handler.headers, body)
    except Exception as exc:
        send_json(handler, {"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
        return

    upload = fields.get("file")
    if not upload or not upload.get("filename"):
        send_json(handler, {"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
        return

    use_llm = flag_value(fields.get("use_llm", {}).get("value"))
    use_cache = flag_value(fields.get("use_cache", {}).get("value"))
    parser_mode = str(fields.get("tender_parser_mode", {}).get("value") or detect_tender_parser_mode()).strip().lower()
    source_path = persist_upload(str(upload["filename"]), bytes(upload["content"]))
    job_id = create_review_job(
        Path(source_path).name,
        source_path,
        use_cache=use_cache,
        use_llm=use_llm,
        parser_mode=parser_mode,
    )
    worker = threading.Thread(
        target=run_review_job,
        args=(job_id, source_path),
        kwargs={"use_cache": use_cache, "use_llm": use_llm, "parser_mode": parser_mode},
        daemon=True,
    )
    worker.start()
    send_json(handler, {"job_id": job_id, "status": "queued", "parser": {"mode": parser_mode, "enabled": parser_mode != "off"}})


def handle_review_status(handler: BaseHTTPRequestHandler, query: str) -> None:
    job_id = parse_qs(query).get("job_id", [""])[0].strip()
    if not job_id:
        send_json(handler, {"error": "缺少 job_id"}, status=HTTPStatus.BAD_REQUEST)
        return
    payload = review_job_status_payload(job_id)
    if payload is None:
        send_json(handler, {"error": "任务不存在"}, status=HTTPStatus.NOT_FOUND)
        return
    send_json(handler, payload)


def handle_review_result(handler: BaseHTTPRequestHandler, query: str) -> None:
    job_id = parse_qs(query).get("job_id", [""])[0].strip()
    if not job_id:
        send_json(handler, {"error": "缺少 job_id"}, status=HTTPStatus.BAD_REQUEST)
        return
    payload = review_job_result_payload(job_id)
    if payload is None:
        send_json(handler, {"error": "任务不存在"}, status=HTTPStatus.NOT_FOUND)
        return
    if payload.get("status") == "failed":
        send_json(handler, payload, status=HTTPStatus.BAD_REQUEST)
        return
    if payload.get("status") != "completed":
        send_json(handler, payload, status=HTTPStatus.ACCEPTED)
        return
    send_json(handler, payload["result"])


def handle_review_submit(handler: BaseHTTPRequestHandler) -> None:
    try:
        body = handler.rfile.read(int(handler.headers.get("Content-Length", "0")))
        fields = parse_multipart(handler.headers, body)
    except Exception as exc:
        send_json(handler, {"error": f"请求解析失败：{exc}"}, status=HTTPStatus.BAD_REQUEST)
        return

    upload = fields.get("file")
    if not upload or not upload.get("filename"):
        send_json(handler, {"error": "缺少上传文件"}, status=HTTPStatus.BAD_REQUEST)
        return

    use_llm = flag_value(fields.get("use_llm", {}).get("value"))
    use_cache = flag_value(fields.get("use_cache", {}).get("value"))
    parser_mode = str(fields.get("tender_parser_mode", {}).get("value") or detect_tender_parser_mode()).strip().lower()
    source_path = persist_upload(str(upload["filename"]), bytes(upload["content"]))
    review_run = run_review_sync(
        source_path,
        use_cache=use_cache,
        use_llm=use_llm,
        parser_mode=parser_mode,
    )
    send_json(handler, build_review_web_payload(review_run))


__all__ = [
    "handle_export_review",
    "handle_open_source",
    "handle_review_result",
    "handle_review_start",
    "handle_review_status",
    "handle_review_submit",
]
