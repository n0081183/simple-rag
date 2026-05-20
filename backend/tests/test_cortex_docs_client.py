"""Tests for vendored cortex-docs-sync client (429-safe rate limiting)."""

import sys
import time
from pathlib import Path

_VENDOR = Path(__file__).resolve().parents[2] / "runpod" / "cortex_docs_sync_vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from cortex_docs_sync.client import CortexDocsClient, RateLimiter  # noqa: E402


def test_rate_limiter_enforces_spacing():
    limiter = RateLimiter(requests_per_second=5.0)
    t0 = time.monotonic()
    for _ in range(3):
        limiter.wait()
    assert time.monotonic() - t0 >= 0.35


def test_backoff_429_uses_retry_after():
    client = CortexDocsClient(max_retries=1)
    class Resp:
        status_code = 429
        headers = {"Retry-After": "15"}

    assert client._backoff_seconds(Resp(), 1) == 15.0


def test_build_sync_cmd_default_rate_in_sync_docs():
    from runpod.pipeline.sync_docs import build_sync_cmd
    import argparse

    args = argparse.Namespace(
        output_dir="/tmp",
        rate_limit=0.5,
        topic_workers=4,
        user_agent="test-ua",
        products=["xdr"],
        full=False,
        include_release_notes=False,
    )
    cmd = build_sync_cmd(args)
    assert "--rate-limit" in cmd
    assert "0.5" in cmd
    assert "--user-agent" in cmd
    assert "--allow-partial-failures" in cmd
