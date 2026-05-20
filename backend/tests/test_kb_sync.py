from app.api.kb import SyncStartRequest
from app.jobs.kb_sync import _pipeline_failure_message, run_kb_sync_job


def test_pipeline_failure_message_uses_stdout_when_stderr_empty():
    msg = _pipeline_failure_message(
        1,
        out="Done: 132 fetched\nFailed: 1\n  - Cortex XSOAR Multi-Tenant Guide",
        err="",
        recent_log=[],
    )
    assert "exit 1" in msg
    assert "Multi-Tenant Guide" in msg


def test_pipeline_failure_message_falls_back_to_recent_log():
    msg = _pipeline_failure_message(1, "", "", ["line1", "FAILED: pipeline failed"])
    assert "FAILED: pipeline failed" in msg


def test_sync_start_request_custom_rate():
    req = SyncStartRequest(rate_limit_rps=0.5, topic_workers=2)
    assert req.rate_limit_rps == 0.5
    assert req.topic_workers == 2


def test_kb_sync_dry_run():
    jobs: dict = {"test-job": {"status": "queued", "logs": []}}
    req = SyncStartRequest(pod_id="", dry_run=True)
    run_kb_sync_job("test-job", req, jobs)
    assert jobs["test-job"]["status"] == "completed"
    assert jobs["test-job"].get("dry_run") is True
    assert all(jobs["test-job"]["steps"][s] == "done" for s in jobs["test-job"]["steps"])
