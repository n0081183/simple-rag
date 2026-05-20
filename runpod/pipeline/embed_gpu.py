#!/usr/bin/env python3
"""GPU embedding with BGE-M3 FP16 — batch processing with checkpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch


def _gpu_banner() -> None:
    name = torch.cuda.get_device_name(0)
    props = torch.cuda.get_device_properties(0)
    mem_gb = props.total_memory / (1024**3)
    print(f"[embed] device=cuda gpu={name} vram={mem_gb:.1f}GB", flush=True)
    print(f"[embed] torch.cuda.is_available={torch.cuda.is_available()}", flush=True)


def _progress(i: int, total: int, started: float, log_every: int) -> None:
    if log_every <= 0 or (i + 1) % log_every != 0:
        return
    elapsed = time.monotonic() - started
    rate = (i + 1) / elapsed if elapsed > 0 else 0.0
    pct = 100.0 * (i + 1) / total if total else 0.0
    eta_s = (total - i - 1) / rate if rate > 0 else 0
    print(
        f"[embed] {i + 1}/{total} ({pct:.1f}%) "
        f"{rate:.1f} chunks/s ETA {eta_s / 60:.0f} min",
        flush=True,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="/workspace/chunks.jsonl")
    p.add_argument("--output", default="/workspace/embeddings.jsonl")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--checkpoint-every", type=int, default=5000)
    p.add_argument("--model", default="BAAI/bge-m3")
    p.add_argument(
        "--log-every",
        type=int,
        default=int(os.environ.get("EMBED_LOG_EVERY", "2000")),
        help="Print one progress line every N chunks (0=tqdm if TTY). Default 2000 for SSH logs.",
    )
    args = p.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("ERROR: CUDA not available — embedding must run on GPU pod")
    _gpu_banner()

    # Plain line logs for remote sync UI (tqdm uses \\r and breaks SSH log viewers).
    use_tqdm = args.log_every <= 0 and sys.stdout.isatty() and not os.environ.get("TQDM_DISABLE")

    from FlagEmbedding import BGEM3FlagModel

    t0 = time.monotonic()
    print(f"[embed] loading model {args.model} (FP16 on cuda)…", flush=True)
    model = BGEM3FlagModel(args.model, use_fp16=True, device="cuda")
    print(f"[embed] model ready in {time.monotonic() - t0:.1f}s", flush=True)

    inp = Path(args.input)
    out = Path(args.output)
    ckpt = out.with_suffix(".ckpt.jsonl")

    lines = inp.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    print(f"[embed] chunks to embed: {total} batch_size={args.batch_size}", flush=True)

    start_idx = 0
    if ckpt.is_file():
        start_idx = sum(1 for _ in ckpt.open(encoding="utf-8"))
        print(f"[embed] resuming from chunk {start_idx}", flush=True)

    mode = "a" if start_idx else "w"
    started = time.monotonic()
    first_flush = True

    with ckpt.open(mode, encoding="utf-8") as ckpt_f:
        batch_records: list[dict] = []
        batch_texts: list[str] = []

        line_iter = lines
        if use_tqdm:
            from tqdm import tqdm

            line_iter = tqdm(lines, desc="embed", mininterval=5.0)

        for i, line in enumerate(line_iter):
            if i < start_idx:
                continue
            rec = json.loads(line)
            text = rec.get("text", "")[:8192]
            batch_records.append(rec)
            batch_texts.append(text)

            if len(batch_texts) < args.batch_size:
                continue

            if first_flush:
                _log_encode_device(model)
                first_flush = False

            _flush(batch_records, batch_texts, model, ckpt_f)
            batch_records, batch_texts = [], []

            if not use_tqdm:
                _progress(i, total, started, args.log_every)

            if (i + 1) % args.checkpoint_every == 0:
                print(f"[embed] checkpoint at {i + 1}", flush=True)

        if batch_texts:
            if first_flush:
                _log_encode_device(model)
            _flush(batch_records, batch_texts, model, ckpt_f)

    ckpt.rename(out)
    elapsed = time.monotonic() - started
    rate = (total - start_idx) / elapsed if elapsed > 0 else 0
    print(f"[embed] wrote {out} ({total - start_idx} chunks in {elapsed / 60:.1f} min, {rate:.1f} chunks/s)", flush=True)


def _log_encode_device(model) -> None:
    try:
        inner = getattr(model, "model", model)
        dev = next(inner.parameters()).device
        print(f"[embed] encode tensors on device={dev}", flush=True)
    except Exception as exc:
        print(f"[embed] could not probe model device: {exc}", flush=True)


def _flush(records, texts, model, out_f):
    out = model.encode(texts, return_dense=True, return_sparse=True, max_length=8192)
    dense = out["dense_vecs"]
    lexical = out["lexical_weights"]
    for rec, d, lex in zip(records, dense, lexical):
        rec["dense"] = d.tolist()
        rec["sparse_indices"] = [int(k) for k in lex.keys()]
        rec["sparse_values"] = [float(v) for v in lex.values()]
        out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
