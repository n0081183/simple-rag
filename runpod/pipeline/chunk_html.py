#!/usr/bin/env python3
"""Chunk HTML documentation for embedding (placeholder — Milestone 2)."""

import argparse
import json
from pathlib import Path

from selectolax.parser import HTMLParser


def chunk_file(path: Path, product: str, max_chars: int = 4000) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    tree = HTMLParser(html)
    title = tree.css_first("title")
    pub_title = title.text() if title else path.stem
    chunks = []
    for i, section in enumerate(tree.css("section")):
        h2 = section.css_first("h2")
        topic = h2.text() if h2 else ""
        text = section.text(separator="\n", strip=True)
        if len(text) < 50:
            continue
        url_el = section.css_first("a")
        topic_url = url_el.attributes.get("href", "") if url_el else ""
        chunks.append(
            {
                "product": product,
                "publication_title": pub_title,
                "topic_breadcrumb": topic,
                "source_url": topic_url,
                "source_file": str(path.name),
                "chunk_index": i,
                "text": text[:max_chars],
                "char_count": len(text),
            }
        )
    return chunks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="/workspace/cortex_docs")
    p.add_argument("--output", default="/workspace/chunks.jsonl")
    args = p.parse_args()
    root = Path(args.input_dir)
    out = Path(args.output)
    count = 0
    with out.open("w", encoding="utf-8") as f:
        for html_path in root.glob("*/*.html"):
            product = html_path.parent.name
            for ch in chunk_file(html_path, product):
                f.write(json.dumps(ch, ensure_ascii=False) + "\n")
                count += 1
    print(f"[chunk] wrote {count} chunks → {out}")


if __name__ == "__main__":
    main()
