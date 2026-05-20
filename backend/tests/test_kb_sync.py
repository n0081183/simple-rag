from app.api.kb import SyncStartRequest
from app.jobs.kb_sync import run_kb_sync_job


def test_kb_sync_dry_run():
    jobs: dict = {"test-job": {"status": "queued", "logs": []}}
    req = SyncStartRequest(pod_id="", dry_run=True)
    run_kb_sync_job("test-job", req, jobs)
    assert jobs["test-job"]["status"] == "completed"
    assert jobs["test-job"].get("dry_run") is True
    assert all(jobs["test-job"]["steps"][s] == "done" for s in jobs["test-job"]["steps"])
