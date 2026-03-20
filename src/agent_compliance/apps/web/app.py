from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from agent_compliance.apps.web.incubator.definition_page import incubator_definition_html
from agent_compliance.apps.web.incubator.definition_routes import (
    handle_requirement_definition_submit,
    incubator_template_payload,
)
from agent_compliance.apps.web.incubator.page import incubator_html
from agent_compliance.apps.web.incubator.routes import (
    handle_incubator_continue,
    handle_incubator_recommendation_update,
    handle_incubator_run_detail,
    handle_incubator_run_compare,
    handle_incubator_start,
    incubator_blueprints_payload,
    list_incubator_runs,
)
from agent_compliance.apps.web.review import (
    review_buyer_html,
    review_fresh_html,
    review_home_html,
    review_next_html,
)
from agent_compliance.apps.web.review.routes import (
    handle_export_review,
    handle_open_source,
    handle_review_result,
    handle_review_start,
    handle_review_status,
    handle_review_submit,
)
from agent_compliance.apps.web.rules.page import rules_html
from agent_compliance.apps.web.rules.routes import handle_rule_decision, rules_payload
from agent_compliance.apps.web.shared.http import send_html, send_json


def run_web_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), ReviewWebHandler)
    print(f"Web UI running at http://{host}:{port}")
    server.serve_forever()


class ReviewWebHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            send_html(self, review_home_html())
            return
        if path == "/review-buyer":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/review-check")
            self.end_headers()
            return
        if path == "/review-next":
            send_html(self, review_next_html())
            return
        if path == "/review-check":
            send_html(self, review_buyer_html())
            return
        if path == "/review-fresh":
            send_html(self, review_fresh_html())
            return
        if path == "/rules":
            send_html(self, rules_html())
            return
        if path == "/incubator":
            send_html(self, incubator_html())
            return
        if path == "/incubator/definition":
            send_html(self, incubator_definition_html())
            return
        if path == "/api/rules":
            send_json(self, rules_payload())
            return
        if path == "/api/incubator/blueprints":
            send_json(self, {"blueprints": incubator_blueprints_payload()})
            return
        if path == "/api/incubator/blueprint-templates":
            send_json(self, {"templates": incubator_template_payload()})
            return
        if path == "/api/incubator/runs":
            send_json(self, {"runs": list_incubator_runs()})
            return
        if path == "/api/incubator/run":
            handle_incubator_run_detail(self, parsed.query)
            return
        if path == "/api/incubator/run-compare":
            handle_incubator_run_compare(self, parsed.query)
            return
        if path == "/api/review-status":
            handle_review_status(self, parsed.query)
            return
        if path == "/api/review-result":
            handle_review_result(self, parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/open-source":
            handle_open_source(self)
            return
        if path == "/api/export-review":
            handle_export_review(self)
            return
        if path == "/api/rules/decision":
            handle_rule_decision(self)
            return
        if path == "/api/incubator/start":
            handle_incubator_start(self)
            return
        if path == "/api/incubator/continue":
            handle_incubator_continue(self)
            return
        if path == "/api/incubator/definition":
            handle_requirement_definition_submit(self)
            return
        if path == "/api/incubator/recommendation":
            handle_incubator_recommendation_update(self)
            return
        if path == "/api/review-start":
            handle_review_start(self)
            return
        if path == "/api/review":
            handle_review_submit(self)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def log_message(self, format: str, *args) -> None:
        return


__all__ = ["ReviewWebHandler", "run_web_server"]
