#!/usr/bin/env python3
"""Fetch Cortex documentation via cortex-docs-sync (RunPod)."""

from __future__ import annotations

import argparse
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
    ]
    if args.products:
        cmd.extend(["--product", *args.products])
    if args.full:
        cmd.append("--full")
    if args.include_release_notes:
        cmd.append("--include-release-notes")
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
    p.add_argument("--rate-limit", type=float, default=2.0)
    args = p.parse_args()

    cmd = build_sync_cmd(args)
    print("[docs-sync]", " ".join(cmd), flush=True)
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
