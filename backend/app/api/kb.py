"""Knowledge base metadata and sync job API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.kb.manifest import load_manifest
from app.core.kb.store import KnowledgeStore
from app.config import get_settings
from app.infra.runpod import RunPodClient

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

_sync_jobs: dict[str, dict] = {}


class ProductInfo(BaseModel):
    product: str
    chunk_count: int


class KBStatusResponse(BaseModel):
    loaded: bool
    products: list[ProductInfo]
    build_date: str | None = None
    embedding_model: str | None = None


class SyncStartRequest(BaseModel):
    products: list[str] = Field(
        default_factory=lambda: ["xdr", "xsiam", "xsoar", "xpanse", "cortex_cloud", "agentix"]
    )
    incremental: bool = True
    pod_id: str = ""
    ssh_host: str | None = None
    ssh_port: int = 22
    ssh_key_path: str | None = None
    include_release_notes: bool = False
    dry_run: bool = False
    rate_limit_rps: float = Field(
        default=1.0,
        ge=0.1,
        le=4.0,
        description="HTTP req/s per download thread (aggregate ≈ rate × topic_workers)",
    )
    topic_workers: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Parallel topic downloads per publication",
    )


class SyncJobResponse(BaseModel):
    job_id: str
    status: str


@router.get("/status", response_model=KBStatusResponse)
def kb_status():
    settings = get_settings()
    manifest_path = settings.kb_active_path / "manifest.json"
    if not manifest_path.is_file():
        return KBStatusResponse(loaded=False, products=[])
    manifest = load_manifest(manifest_path)
    store = KnowledgeStore(settings.kb_active_path)
    products = store.list_products()
    return KBStatusResponse(
        loaded=True,
        products=[ProductInfo(product=p, chunk_count=c) for p, c in products],
        build_date=manifest.build_date,
        embedding_model=manifest.embedding_model,
    )


@router.get("/products")
def list_products():
    """Dynamic product list from KB metadata."""
    settings = get_settings()
    store = KnowledgeStore(settings.kb_active_path)
    return {"products": [{"id": p, "chunk_count": c} for p, c in store.list_products()]}


@router.post("/sync", response_model=SyncJobResponse)
def start_sync(body: SyncStartRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _sync_jobs[job_id] = {"status": "queued", "logs": []}

    def run():
        from app.jobs.kb_sync import run_kb_sync_job

        run_kb_sync_job(job_id, body, _sync_jobs)

    background_tasks.add_task(run)
    return SyncJobResponse(job_id=job_id, status="queued")


@router.get("/sync/{job_id}")
def get_sync_status(job_id: str):
    job = _sync_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Sync job not found")
    return job


@router.post("/test-connection")
def kb_test_connection(body: SyncStartRequest):
    try:
        from app.jobs.kb_sync import test_connection

        return test_connection(body)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/pods/{pod_id}/stop")
def stop_pod(pod_id: str):
    try:
        RunPodClient().stop_pod(pod_id)
        return {"ok": True, "pod_id": pod_id}
    except Exception as e:
        raise HTTPException(400, str(e)) from e
