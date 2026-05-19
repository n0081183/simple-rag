#!/usr/bin/env python3
"""Fetch Cortex documentation via cortex-docs-sync (RunPod)."""

import argparse
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="/workspace/cortex_docs")
    p.add_argument("--products", nargs="*", default=None)
    p.add_argument("--incremental", action="store_true", default=True)
    p.add_argument("--rate-limit", type=float, default=2.0)
    args = p.parse_args()

    cmd = [
        "cortex-docs-sync",
        "--output-dir",
        args.output_dir,
        "--rate-limit",
        str(args.rate_limit),
    ]
    if args.products:
        cmd.extend(["--product", *args.products])
    if not args.incremental:
        cmd.append("--full")

    print("[docs-sync]", " ".join(cmd), flush=True)
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
