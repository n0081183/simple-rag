"""Anthropic API provider (premium quality opt-in)."""

from __future__ import annotations

import json
import logging

import httpx

from app.infra.keychain import get_secret

logger = logging.getLogger(__name__)


class AnthropicProvider:
    def __init__(self):
        self.api_key = get_secret("anthropic_api_key")
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")

    def complete_json(self, system: str, user: str) -> dict:
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        with httpx.Client(timeout=120.0) as client:
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
            logger.warning("anthropic_non_json_response")
            return {}
