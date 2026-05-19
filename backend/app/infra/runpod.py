"""RunPod REST API client for pod lifecycle and connection test."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.infra.keychain import get_secret

logger = logging.getLogger(__name__)

RUNPOD_API = "https://api.runpod.io/graphql"
RUNPOD_REST = "https://rest.runpod.io/v1"


@dataclass
class PodInfo:
    pod_id: str
    name: str
    gpu_type: str | None
    status: str
    public_ip: str | None


class RunPodClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_secret("runpod_api_key")
        if not self.api_key:
            raise ValueError("RunPod API key not configured (use Settings)")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_pod(self, pod_id: str) -> PodInfo:
        """Fetch pod metadata via REST (simplified; full GraphQL in Milestone 2)."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{RUNPOD_REST}/pods/{pod_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return PodInfo(
            pod_id=pod_id,
            name=data.get("name", pod_id),
            gpu_type=data.get("gpuType"),
            status=data.get("desiredStatus", "unknown"),
            public_ip=data.get("publicIp"),
        )

    def stop_pod(self, pod_id: str) -> None:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{RUNPOD_REST}/pods/{pod_id}/stop",
                headers=self._headers(),
            )
            resp.raise_for_status()
        logger.info("runpod_pod_stopped pod_id=%s", pod_id)
