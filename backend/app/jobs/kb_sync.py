"""Local orchestrator for RunPod KB sync (Function B) — SSH + pipeline."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from app.api.kb import SyncStartRequest
from app.config import get_settings
from app.core.kb.ingest import build_seed_kb
from app.core.kb.snapshot import extract_tar_zst, install_snapshot
from app.core.kb.swap import atomic_swap
from app.infra.runpod import RunPodClient
from app.infra.ssh import SSHConfig, SSHSession, test_ssh_connection

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

REMOTE_WORKSPACE = "/workspace"
REMOTE_SNAPSHOT = f"{REMOTE_WORKSPACE}/kb_snapshot.tar.zst"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_kb_sync_job(job_id: str, request: SyncStartRequest, jobs: dict) -> None:
    job = jobs.get(job_id)
    if not isinstance(job, dict):
        raise TypeError(f"Invalid sync job record for {job_id!r}")
    job["status"] = "running"
    job["steps"] = {s: "pending" for s in STEPS}
    job["logs"] = job.get("logs", [])
    job["progress_pct"] = 0

    def log(msg: str):
        entry = f"[{datetime.now(UTC).isoformat()}] {msg}"
        job["logs"].append(entry)
        logger.info("kb_sync job=%s %s", job_id, msg)

    def set_step(step: str, state: str):
        job["steps"][step] = state
        done = sum(1 for s in STEPS if job["steps"].get(s) == "done")
        job["progress_pct"] = int(100 * done / len(STEPS))

    try:
        if request.dry_run:
            _run_dry(job, request, log, set_step)
            return

        ssh_host, ssh_port = _resolve_ssh(request, log)
        ssh_cfg = SSHConfig(
            host=ssh_host,
            port=ssh_port,
            private_key_path=request.ssh_key_path,
        )

        with SSHSession(ssh_cfg) as ssh:
            _run_remote_pipeline(ssh, request, log, set_step)

        set_step("download_local", "running")
        log("Downloading snapshot from pod…")
        settings = get_settings()
        staging = settings.kb_staging_path
        archive = staging / "kb_snapshot.tar.zst"
        staging.mkdir(parents=True, exist_ok=True)

        with SSHSession(ssh_cfg) as ssh:

            def prog(done: int, total: int):
                if total:
                    job["download_pct"] = int(100 * done / total)

            ssh.download_file(REMOTE_SNAPSHOT, archive, on_progress=prog)
        log(f"Downloaded {archive.stat().st_size / 1e6:.1f} MB")
        set_step("download_local", "done")

        set_step("atomic_swap", "running")
        log("Extracting and validating snapshot…")
        install_snapshot(archive, staging)
        manifest = atomic_swap(staging)
        log(f"KB active — {manifest.total_chunks} chunks")
        set_step("atomic_swap", "done")

        job["status"] = "completed"
        job["manifest"] = manifest.model_dump()
        log("Sync completed successfully")
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        log(f"FAILED: {e}")
        logger.exception("kb_sync_failed job=%s", job_id)


def _resolve_ssh(request: SyncStartRequest, log) -> tuple[str, int]:
    if request.ssh_host:
        return request.ssh_host, request.ssh_port or 22
    client = RunPodClient()
    info = client.get_pod(request.pod_id)
    if not info.public_ip:
        raise ValueError("Pod has no public IP — set ssh_host manually in UI")
    log(f"Pod {info.name}: GPU={info.gpu_type}, IP={info.public_ip}")
    return info.public_ip, request.ssh_port or info.ssh_port or 22


def _pipeline_failure_message(code: int, out: str, err: str, recent_log: list[str]) -> str:
    """Build a useful error when SSH stderr is empty (common with PTY)."""
    combined = (out or "").strip()
    if err and err.strip():
        combined = f"{combined}\n{err.strip()}".strip() if combined else err.strip()
    tail = combined.splitlines()[-5:] if combined else []
    if not tail and recent_log:
        tail = recent_log[-5:]
    hint = "\n".join(tail) if tail else "see job logs above (docs-sync / pipeline output)"
    return (
        f"pipeline failed (exit {code}). "
        f"If docs-sync shows Failed:N with 429, pull latest runpod/ and re-bootstrap. "
        f"{hint}"
    )


def _run_remote_pipeline(ssh: SSHSession, request: SyncStartRequest, log, set_step) -> None:
    root = _repo_root()
    runpod_dir = root / "runpod"
    recent: list[str] = []

    def log_and_remember(msg: str) -> None:
        recent.append(msg)
        if len(recent) > 80:
            del recent[:-80]
        log(msg)

    set_step("bootstrap", "running")
    log("Uploading runpod/ scripts to pod…")
    ssh.run(f"mkdir -p {REMOTE_WORKSPACE}/runpod")
    ssh.upload_tree(runpod_dir, f"{REMOTE_WORKSPACE}/runpod")
    ssh.run(f"chmod +x {REMOTE_WORKSPACE}/runpod/bootstrap.sh {REMOTE_WORKSPACE}/runpod/pipeline/run_all.sh")

    code, _, _ = ssh.run(f"test -f {REMOTE_WORKSPACE}/.bootstrap_ok")
    if code == 0:
        log("Bootstrap marker found — quick verify (skip reinstall if OK)")
    else:
        log("Running bootstrap.sh (staged pip + swap; first run often 10–20 min)…")

    code, bout, err = ssh.run(
        f"WORKSPACE={REMOTE_WORKSPACE} bash {REMOTE_WORKSPACE}/runpod/bootstrap.sh",
        on_line=log_and_remember,
    )
    if code != 0:
        raise RuntimeError(_pipeline_failure_message(code, bout, err, recent).replace("pipeline", "bootstrap"))
    set_step("bootstrap", "done")
    set_step("clone_docs_sync", "done")

    set_step("sync_docs", "running")
    products = " ".join(request.products)
    incr = "1" if request.incremental else "0"
    rn = "1" if request.include_release_notes else "0"
    rate_limit = os.environ.get("CORTEX_DOCS_RATE_LIMIT", "0.35")
    topic_workers = os.environ.get("CORTEX_SYNC_TOPIC_WORKERS", "1")
    pipeline_cmd = (
        f"WORKSPACE={REMOTE_WORKSPACE} PRODUCTS='{products}' INCREMENTAL={incr} "
        f"INCLUDE_RELEASE_NOTES={rn} EMBED_BATCH_SIZE=64 "
        f"RATE_LIMIT={rate_limit} CORTEX_SYNC_TOPIC_WORKERS={topic_workers} "
        f"bash {REMOTE_WORKSPACE}/runpod/pipeline/run_all.sh"
    )
    log("Starting full pipeline on pod (sync → chunk → embed → index → export)…")
    code, out, err = ssh.run(pipeline_cmd, on_line=log_and_remember)
    if code != 0:
        raise RuntimeError(_pipeline_failure_message(code, out, err, recent))
    for s in ("sync_docs", "chunk_html", "embed_gpu", "build_index", "export_snapshot"):
        set_step(s, "done")


def _run_dry(job: dict, request: SyncStartRequest, log, set_step) -> None:
    """Local dry-run: seed KB without SSH (dev/CI)."""
    log("DRY RUN — building local seed KB (no RunPod)")
    for step in STEPS:
        set_step(step, "running")
        log(f"[dry-run] {step}")
        set_step(step, "done")
    settings = get_settings()
    build_seed_kb(settings.kb_active_path, skip_ml=True)
    job["status"] = "completed"
    job["dry_run"] = True
    log("Dry run complete — seed KB installed at kb-active")


def test_connection(request: SyncStartRequest) -> dict:
    if request.dry_run:
        build_seed_kb(get_settings().kb_active_path, skip_ml=True)
        return {"ok": True, "mode": "dry_run", "message": "Local seed KB built"}
    ssh_host, ssh_port = _resolve_ssh(request, lambda m: None)
    return test_ssh_connection(
        SSHConfig(host=ssh_host, port=ssh_port, private_key_path=request.ssh_key_path)
    )

