import pytest
from pydantic import ValidationError

from app.api.kb import SyncStartRequest


def test_sync_start_request_rate_defaults():
    req = SyncStartRequest()
    assert req.rate_limit_rps == 0.35
    assert req.topic_workers == 1


def test_sync_start_request_rate_bounds():
    SyncStartRequest(rate_limit_rps=0.1, topic_workers=4)
    with pytest.raises(ValidationError):
        SyncStartRequest(rate_limit_rps=3.0)
    with pytest.raises(ValidationError):
        SyncStartRequest(topic_workers=0)
