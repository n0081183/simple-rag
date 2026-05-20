#!/usr/bin/env python3
"""Build LanceDB index from embedded chunks."""

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="/workspace/embeddings.jsonl")
    p.add_argument("--output-dir", default="/workspace/kb_build")
    p.add_argument("--model", default="BAAI/bge-m3")
    args = p.parse_args()

    import lancedb

    out_dir = Path(args.output_dir)
    lance_path = out_dir / "lance"
    lance_path.mkdir(parents=True, exist_ok=True)

    rows = []
    product_counts: dict[str, int] = defaultdict(int)

    for line in Path(args.input).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        pid = rec.get("id") or f"{rec['source_file']}-{rec.get('chunk_index', 0)}"
        product = rec.get("product", "unknown")
        product_counts[product] += 1
        header = ""
        if rec.get("topic_breadcrumb"):
            header = f"[{rec['topic_breadcrumb']}]\n"
        if rec.get("publication_title"):
            header = f"# {rec['publication_title']}\n{header}"
        text = header + rec.get("text", "")

        rows.append(
            {
                "id": str(pid),
                "text": text,
                "product": product,
                "dense": rec["dense"],
                "sparse_indices": json.dumps(rec.get("sparse_indices", [])),
                "sparse_values": json.dumps(rec.get("sparse_values", [])),
                "source_file": rec.get("source_file", ""),
                "topic_url": rec.get("source_url", ""),
                "metadata": json.dumps(
                    {
                        "publication_title": rec.get("publication_title"),
                        "chunk_index": rec.get("chunk_index"),
                    }
                ),
            }
        )

    db = lancedb.connect(str(lance_path))
    if "chunks" in db.list_tables():
        db.drop_table("chunks")
    db.create_table("chunks", data=rows, mode="overwrite")
    print(f"[index] {len(rows)} chunks indexed")

    manifest = {
        "version": "1",
        "build_date": datetime.now(UTC).isoformat(),
        "embedding_model": args.model,
        "embedding_dim": len(rows[0]["dense"]) if rows else 1024,
        "schema_version": "1",
        "total_chunks": len(rows),
        "products": {p: {"chunk_count": c} for p, c in product_counts.items()},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    capsules = {}
    by_product: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_product[r["product"]].append(r["text"][:500])
    for prod, texts in by_product.items():
        capsules[prod] = "\n".join(texts[:3])[:4000]
    (out_dir / "product_capsules.json").write_text(
        json.dumps(capsules, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[index] manifest + capsules → {out_dir}")


if __name__ == "__main__":
    main()
