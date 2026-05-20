#!/usr/bin/env python3
"""Fetch Cortex documentation via cortex-docs-sync (RunPod)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def build_sync_cmd(args: argparse.Namespace) -> list[str]:
    """Build cortex-docs-sync CLI argv from parsed args."""
    cmd = [
        "cortex-docs-sync",
        "--output-dir",
        args.output_dir,
        "--rate-limit",
        str(args.rate_limit),
        "--topic-workers",
        str(args.topic_workers),
        "--user-agent",
        args.user_agent,
    ]
    if args.products:
        cmd.extend(["--product", *args.products])
    if args.full:
        cmd.append("--full")
    if args.include_release_notes:
        cmd.append("--include-release-notes")
    strict = os.environ.get("CORTEX_SYNC_STRICT", "").lower() in ("1", "true", "yes")
    allow_partial = os.environ.get("CORTEX_ALLOW_PARTIAL", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    if strict or not allow_partial:
        cmd.append("--strict")
    else:
        cmd.append("--allow-partial-failures")
    return cmd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="/workspace/cortex_docs")
    p.add_argument(
        "--product",
        "--products",
        dest="products",
        nargs="+",
        default=None,
        metavar="PRODUCT",
        help="Product slugs: xdr xsiam xsoar xpanse cortex_cloud agentix",
    )
    p.add_argument("--full", action="store_true", help="Full rebuild (not incremental)")
    p.add_argument("--include-release-notes", action="store_true")
    p.add_argument(
        "--rate-limit",
        type=float,
        default=float(os.environ.get("RATE_LIMIT", "1.0")),
        help="HTTP req/s per thread (default 1.0)",
    )
    p.add_argument(
        "--topic-workers",
        type=int,
        default=int(os.environ.get("CORTEX_SYNC_TOPIC_WORKERS", "4")),
        help="Parallel topic workers per publication",
    )
    p.add_argument(
        "--user-agent",
        default=os.environ.get(
            "CORTEX_DOCS_USER_AGENT",
            "Mozilla/5.0 (compatible; Cortex-Workbench/1.0) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        ),
    )
    args = p.parse_args()

    cmd = build_sync_cmd(args)
    print("[docs-sync]", " ".join(cmd), flush=True)
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
