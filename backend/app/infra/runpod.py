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
    ssh_port: int = 22


class RunPodClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_secret("runpod_api_key")
        if not self.api_key:
            raise ValueError("RunPod API key not configured (use Settings)")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_pod(self, pod_id: str) -> PodInfo:
        """Fetch pod metadata via RunPod REST API."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{RUNPOD_REST}/pods/{pod_id}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return self._get_pod_graphql(pod_id)
            resp.raise_for_status()
            data = resp.json()
        return self._parse_pod(pod_id, data)

    def _get_pod_graphql(self, pod_id: str) -> PodInfo:
        query = """
        query Pod($input: PodQueryInput!) {
          pod(input: $input) { id name desiredStatus
            runtime { ports { ip isIpPublic privatePort publicPort type } }
            machine { gpuDisplayName }
          }
        }
        """
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                RUNPOD_API,
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"query": query, "variables": {"input": {"podId": pod_id}}},
            )
            resp.raise_for_status()
            data = resp.json()["data"]["pod"]
        ip, port = None, 22
        for p in data.get("runtime", {}).get("ports", []) or []:
            if p.get("privatePort") == 22 and p.get("isIpPublic"):
                ip = p.get("ip")
                port = int(p.get("publicPort") or 22)
        return PodInfo(
            pod_id=pod_id,
            name=data.get("name", pod_id),
            gpu_type=(data.get("machine") or {}).get("gpuDisplayName"),
            status=data.get("desiredStatus", "unknown"),
            public_ip=ip,
            ssh_port=port,
        )

    def _parse_pod(self, pod_id: str, data: dict) -> PodInfo:
        ip = data.get("publicIp") or data.get("ip")
        port = 22
        for p in data.get("ports", []) or data.get("runtime", {}).get("ports", []) or []:
            if p.get("privatePort") == 22:
                ip = ip or p.get("ip")
                port = int(p.get("publicPort") or port)
        return PodInfo(
            pod_id=pod_id,
            name=data.get("name", pod_id),
            gpu_type=data.get("gpuType") or data.get("gpuDisplayName"),
            status=data.get("desiredStatus", "unknown"),
            public_ip=ip,
            ssh_port=port,
        )

    def stop_pod(self, pod_id: str) -> None:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{RUNPOD_REST}/pods/{pod_id}/stop",
                headers=self._headers(),
            )
            resp.raise_for_status()
        logger.info("runpod_pod_stopped pod_id=%s", pod_id)
