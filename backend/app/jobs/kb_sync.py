"""Local orchestrator for RunPod KB sync (Function B)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.api.kb import SyncStartRequest

logger = logging.getLogger(__name__)

STEPS = [
    "bootstrap",
    "clone_docs_sync",
    "sync_docs",
    "chunk_html",
    "embed_gpu",
    "build_index",
    "export_snapshot",
    "download_local",
    "atomic_swap",
]


def run_kb_sync_job(job_id: str, request: SyncStartRequest, jobs: dict) -> None:
    """Execute sync pipeline; Milestone 0 logs steps, M2 runs SSH."""
    job = jobs[job_id]
    job["status"] = "running"
    job["steps"] = {s: "pending" for s in STEPS}
    job["logs"] = []

    def log(msg: str):
        entry = f"[{datetime.now(UTC).isoformat()}] {msg}"
        job["logs"].append(entry)
        logger.info("kb_sync job=%s %s", job_id, msg)

    try:
        for step in STEPS:
            job["steps"][step] = "running"
            log(f"Starting: {step}")
            if step == "bootstrap":
                log("[mock] Would run runpod/bootstrap.sh via SSH")
            elif step == "sync_docs":
                log(f"[mock] cortex-docs-sync products={request.products}")
            elif step == "download_local":
                log("[mock] scp snapshot.tar.zst → kb-staging")
            elif step == "atomic_swap":
                log("[mock] validate manifest + atomic swap")
            job["steps"][step] = "done"
        job["status"] = "completed"
        log("Sync job completed (Milestone 0 mock)")
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        log(f"FAILED: {e}")
