from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import request

from agent_compliance.config import LLMConfig


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class OpenAICompatibleLLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        payload = {
            "model": self._config.model,
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
        with request.urlopen(req, timeout=self._config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers
