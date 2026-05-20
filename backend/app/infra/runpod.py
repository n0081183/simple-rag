"""RunPod REST API client for pod lifecycle and connection test."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _iter_ports(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect SSH port entries from REST/GraphQL pod payloads."""
    entries: list[dict[str, Any]] = []

    def add_from(container: dict[str, Any]) -> None:
        raw = container.get("ports")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    entries.append(item)

    add_from(data)
    runtime = data.get("runtime")
    if isinstance(runtime, dict):
        add_from(runtime)
    return entries


def _unwrap_pod_payload(raw: Any, pod_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Unexpected RunPod response for pod {pod_id}: expected object, got {type(raw).__name__}")
    if isinstance(raw.get("pod"), dict):
        return raw["pod"]
    inner = raw.get("data")
    if isinstance(inner, dict) and isinstance(inner.get("pod"), dict):
        return inner["pod"]
    return raw


class RunPodClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_secret("runpod_api_key")
        if not self.api_key:
            raise ValueError("RunPod API key not configured (use Settings)")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_pod(self, pod_id: str) -> PodInfo:
        """Fetch pod metadata via RunPod REST API."""
        if not pod_id or not str(pod_id).strip():
            raise ValueError("Pod ID is required (or set SSH host manually)")
        pod_id = str(pod_id).strip()

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{RUNPOD_REST}/pods/{pod_id}",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return self._get_pod_graphql(pod_id)
            resp.raise_for_status()
            data = _unwrap_pod_payload(resp.json(), pod_id)
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
            body = resp.json()
        errors = body.get("errors")
        if errors:
            msg = errors[0].get("message", str(errors)) if isinstance(errors[0], dict) else str(errors)
            raise ValueError(f"RunPod GraphQL error: {msg}")
        data_root = body.get("data") or {}
        pod = data_root.get("pod") if isinstance(data_root, dict) else None
        if not isinstance(pod, dict):
            raise ValueError(f"Pod {pod_id} not found in RunPod")
        return self._parse_pod(pod_id, pod)

    def _parse_pod(self, pod_id: str, data: dict[str, Any]) -> PodInfo:
        ip = data.get("publicIp") or data.get("ip")
        port = 22
        for p in _iter_ports(data):
            if p.get("privatePort") == 22:
                ip = ip or p.get("ip")
                port = int(p.get("publicPort") or port)
            if p.get("isIpPublic") and p.get("privatePort") == 22:
                ip = p.get("ip") or ip
                port = int(p.get("publicPort") or port)

        machine_raw = data.get("machine")
        gpu = data.get("gpuType") or data.get("gpuDisplayName")
        if not gpu and isinstance(machine_raw, str):
            gpu = machine_raw
        elif not gpu and isinstance(machine_raw, dict):
            gpu = machine_raw.get("gpuDisplayName")
        runtime = data.get("runtime")
        status = data.get("desiredStatus") or data.get("status") or "unknown"
        if isinstance(runtime, str):
            status = runtime

        return PodInfo(
            pod_id=pod_id,
            name=str(data.get("name") or pod_id),
            gpu_type=gpu,
            status=str(status),
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
