#!/usr/bin/env python3
"""GPU embedding with BGE-M3 FP16 — batch processing with checkpoints."""

import argparse
import json
from pathlib import Path

import torch
from tqdm import tqdm


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="/workspace/chunks.jsonl")
    p.add_argument("--output", default="/workspace/embeddings.jsonl")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--checkpoint-every", type=int, default=5000)
    p.add_argument("--model", default="BAAI/bge-m3")
    args = p.parse_args()

    assert torch.cuda.is_available(), "CUDA required"
    device = "cuda"

    from FlagEmbedding import BGEM3FlagModel

    model = BGEM3FlagModel(args.model, use_fp16=True, device=device)

    inp = Path(args.input)
    out = Path(args.output)
    ckpt = out.with_suffix(".ckpt.jsonl")

    lines = inp.read_text(encoding="utf-8").splitlines()
    start_idx = 0
    if ckpt.is_file():
        start_idx = sum(1 for _ in ckpt.open())
        print(f"[embed] resuming from chunk {start_idx}")

    mode = "a" if start_idx else "w"
    with ckpt.open(mode, encoding="utf-8") as ckpt_f:
        batch_records: list[dict] = []
        batch_texts: list[str] = []

        for i, line in enumerate(tqdm(lines, desc="embed")):
            if i < start_idx:
                continue
            rec = json.loads(line)
            text = rec.get("text", "")[:8192]
            batch_records.append(rec)
            batch_texts.append(text)

            if len(batch_texts) < args.batch_size:
                continue

            _flush(batch_records, batch_texts, model, ckpt_f)
            batch_records, batch_texts = [], []

            if (i + 1) % args.checkpoint_every == 0:
                print(f"[embed] checkpoint at {i + 1}")

        if batch_texts:
            _flush(batch_records, batch_texts, model, ckpt_f)

    ckpt.rename(out)
    print(f"[embed] wrote {out}")


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
