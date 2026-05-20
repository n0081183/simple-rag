"""Unified LLM provider (Ollama default, Anthropic opt-in)."""

from __future__ import annotations

import json
import logging
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.infra.keychain import get_secret

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMProvider:
    def complete_json(self, system: str, user: str, schema: type[T] | None = None) -> dict:
        raise NotImplementedError

    def complete_text(self, system: str, user: str) -> str:
        data = self.complete_json(system, user)
        return data.get("content", "") if isinstance(data, dict) else str(data)


class OllamaProvider(LLMProvider):
    def __init__(self):
        s = get_settings()
        self.base_url = s.ollama_base_url.rstrip("/")
        self.model = s.ollama_model
        self.timeout = s.ollama_timeout_seconds

    def _chat_payload(self, system: str, user: str, *, json_mode: bool) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"num_predict": 768, "temperature": 0.1},
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    def complete_json(self, system: str, user: str, schema: type[T] | None = None) -> dict:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/chat",
                    json=self._chat_payload(system, user, json_mode=True),
                )
                resp.raise_for_status()
                content = resp.json()["message"]["content"]
            return json.loads(content)
        except httpx.TimeoutException as e:
            logger.warning("ollama_timeout model=%s error=%s", self.model, e)
            return {}
        except Exception as e:
            logger.warning("ollama_error error=%s", e)
            return {}

    def complete_text(self, system: str, user: str) -> str:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/chat",
                    json=self._chat_payload(system, user, json_mode=False),
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except httpx.TimeoutException as e:
            logger.warning("ollama_timeout model=%s error=%s", self.model, e)
            return ""
        except Exception as e:
            logger.warning("ollama_error error=%s", e)
            return ""


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.api_key = get_secret("anthropic_api_key")
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")

    def complete_json(self, system: str, user: str, schema: type[T] | None = None) -> dict:
        user_msg = user
        if schema:
            user_msg += f"\n\nRespond with JSON matching this schema:\n{schema.model_json_schema()}"
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user_msg}],
        }
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        try:
            return AnthropicProvider()
        except ValueError:
            pass
    return OllamaProvider()
