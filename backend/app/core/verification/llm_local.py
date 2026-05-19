"""Ollama LLM client for local inference."""

from __future__ import annotations

import json
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class OllamaProvider:
    def __init__(self):
        s = get_settings()
        self.base_url = s.ollama_base_url.rstrip("/")
        self.model = s.ollama_model

    def complete_json(self, system: str, user: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                content = resp.json()["message"]["content"]
            return json.loads(content)
        except Exception as e:
            logger.warning("ollama_unavailable error=%s", e)
            return {}
