from __future__ import annotations

import json
from urllib import error
from dataclasses import dataclass
from urllib import request

from agent_compliance.core.config import LLMConfig


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._resolved_model: str | None = None

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        model = self._resolved_model or self._config.model
        payload = {
            "model": model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self._config.base_url}/chat/completions",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._config.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code in {400, 404} and self._maybe_retry_with_available_model(exc):
                return self.chat(messages, temperature=temperature)
            raise
        return body["choices"][0]["message"]["content"]

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def _maybe_retry_with_available_model(self, exc: error.HTTPError) -> bool:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        requested_model = self._resolved_model or self._config.model
        if requested_model and requested_model in body and "does not exist" in body:
            available = self.list_models()
            if available:
                self._resolved_model = available[0]
                return True
        return False

    def list_models(self) -> list[str]:
        req = request.Request(
            url=f"{self._config.base_url}/models",
            headers=self._headers(),
            method="GET",
        )
        with request.urlopen(req, timeout=self._config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        return [item["id"] for item in body.get("data", []) if item.get("id")]
