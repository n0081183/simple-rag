import argparse
import os
import sys
from unittest.mock import patch

from runpod.pipeline import sync_docs
from runpod.pipeline.sync_docs import build_sync_cmd


def _sync_args(**overrides):
    defaults = dict(
        output_dir="/workspace/cortex_docs",
        rate_limit=1.0,
        topic_workers=4,
        user_agent="test-ua",
        products=["xdr"],
        full=False,
        include_release_notes=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_build_sync_cmd_all_products():
    args = argparse.Namespace(
        output_dir="/workspace/cortex_docs",
        rate_limit=2.0,
        topic_workers=4,
        user_agent="test-ua",
        products=["xdr", "xsiam", "xsoar", "xpanse", "cortex_cloud", "agentix"],
        full=False,
        include_release_notes=False,
    )
    cmd = build_sync_cmd(args)
    assert "--allow-partial-failures" in cmd
    assert "--topic-workers" in cmd
    idx = cmd.index("--product")
    assert cmd[idx + 1 : idx + 7] == [
        "xdr",
        "xsiam",
        "xsoar",
        "xpanse",
        "cortex_cloud",
        "agentix",
    ]


def test_build_sync_cmd_append_products_from_shell():
    """Simulate: --products xdr xsiam xsoar (nargs collects rest)."""
    args = argparse.Namespace(
        output_dir="/out",
        rate_limit=1.0,
        topic_workers=4,
        user_agent="test-ua",
        products=["xdr", "xsiam", "xsoar", "xpanse", "cortex_cloud", "agentix"],
        full=True,
        include_release_notes=True,
    )
    cmd = build_sync_cmd(args)
    assert "--full" in cmd
    assert "--include-release-notes" in cmd
    assert len([x for x in cmd if x in ("xdr", "xsiam", "xpanse")]) == 3


def test_sync_docs_cli_parses_run_all_style_argv():
    """Matches: sync_docs.py --output-dir /workspace/cortex_docs --products xdr xsiam ..."""
    argv = [
        "sync_docs.py",
        "--output-dir",
        "/workspace/cortex_docs",
        "--rate-limit",
        "2.0",
        "--products",
        "xdr",
        "xsiam",
        "xsoar",
        "xpanse",
        "cortex_cloud",
        "agentix",
    ]
    with patch.object(sys, "argv", argv):
        with patch.object(sync_docs, "subprocess") as mock_sp:
            mock_sp.call.return_value = 0
            with patch.object(sys, "exit"):
                sync_docs.main()
    call_cmd = mock_sp.call.call_args[0][0]
    assert "--allow-partial-failures" in call_cmd
    assert call_cmd.count("--product") == 1
    i = call_cmd.index("--product") + 1
    products = call_cmd[i : i + 6]
    assert products == ["xdr", "xsiam", "xsoar", "xpanse", "cortex_cloud", "agentix"]


def test_build_sync_cmd_strict_when_partial_disabled(monkeypatch):
    monkeypatch.setenv("CORTEX_ALLOW_PARTIAL", "0")
    cmd = build_sync_cmd(_sync_args())
    assert "--strict" in cmd
    assert "--allow-partial-failures" not in cmd
