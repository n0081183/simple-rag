"""Build seed knowledge base from bundled domain chunks (dev / eval)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.core.domain_knowledge.product_facts import ARCHITECTURE_FACTS
from app.core.kb.manifest import KBManifest, ProductStats, save_manifest
from app.core.retrieval.embedder import Embedder


def _seed_records() -> list[dict]:
    """Curated chunks for local dev until full cortex-docs sync."""
    records: list[dict] = []
    docs_base = "https://docs-cortex.paloaltonetworks.com"

    product_urls = {
        "xdr": f"{docs_base}/r/Cortex-XDR",
        "xsiam": f"{docs_base}/r/Cortex-XSIAM",
        "xsoar": f"{docs_base}/r/Cortex-XSOAR",
        "xpanse": f"{docs_base}/r/Cortex-XPANSE",
        "cortex_cloud": f"{docs_base}/r/Cortex-Cloud",
        "agentix": f"{docs_base}/r/Cortex-AgentiX",
    }

    extra = [
        (
            "xdr",
            "Cortex XDR Agent supports Windows 10 21H2, 22H2, Windows 11 24H2 and 25H2. "
            "Agent supports macOS 12+, RHEL 8/9, Ubuntu 20.04/22.04, Android and iOS.",
        ),
        (
            "xdr",
            "Cortex XDR provides EDR, exploit prevention, ransomware protection, "
            "USB device control, and WildFire sandbox integration.",
        ),
        (
            "xsiam",
            "Cortex XSIAM runs as SaaS with optional on-premises Broker VM for syslog "
            "and offline buffering. Includes SIEM, SOAR, XDR, and data lake.",
        ),
        (
            "xsoar",
            "Cortex XSOAR supports playbook automation, case management, War Room, "
            "and 700+ integration content packs.",
        ),
        (
            "xpanse",
            "Cortex XPANSE performs external attack surface management: IPv4/IPv6 scanning, "
            "asset discovery, vulnerability and misconfiguration testing.",
        ),
        (
            "cortex_cloud",
            "Cortex Cloud delivers CNAPP capabilities: CSPM, CWPP, CI/CD security scanning.",
        ),
        (
            "agentix",
            "Cortex AgentiX provides AI agents for security operations integrated with XSIAM and XSOAR.",
        ),
    ]

    for product, facts in ARCHITECTURE_FACTS.items():
        key = product.lower()
        for lang in ("pl", "en"):
            text = facts.get(lang, "")
            if text:
                records.append(
                    {
                        "product": key,
                        "text": text,
                        "source_file": f"{key}-overview-{lang}.html",
                        "topic_url": product_urls.get(key, docs_base),
                    }
                )

    for product, text in extra:
        records.append(
            {
                "product": product,
                "text": text,
                "source_file": f"{product}-seed.html",
                "topic_url": product_urls.get(product, docs_base),
            }
        )

    return records


def build_seed_kb(target_path: Path | None = None, skip_ml: bool = False) -> KBManifest:
    import os

    if skip_ml:
        os.environ["SIWZ_SKIP_ML"] = "1"

    settings = get_settings()
    kb_path = target_path or settings.kb_active_path
    kb_path.mkdir(parents=True, exist_ok=True)
    lance_dir = kb_path / "lance"
    lance_dir.mkdir(parents=True, exist_ok=True)

    import lancedb

    embedder = Embedder.get()
    rows = []
    product_counts: dict[str, int] = {}

    for rec in _seed_records():
        emb = embedder.embed(rec["text"])
        pid = str(uuid.uuid4())
        product = rec["product"]
        product_counts[product] = product_counts.get(product, 0) + 1
        rows.append(
            {
                "id": pid,
                "text": rec["text"],
                "product": product,
                "dense": emb.dense,
                "sparse_indices": json.dumps(emb.sparse_indices),
                "sparse_values": json.dumps(emb.sparse_values),
                "source_file": rec["source_file"],
                "topic_url": rec["topic_url"],
                "metadata": "{}",
            }
        )

    db = lancedb.connect(str(lance_dir))
    if "chunks" in db.list_tables():
        db.drop_table("chunks")
    db.create_table("chunks", data=rows, mode="overwrite")

    manifest = KBManifest(
        build_date=datetime.now(UTC).isoformat(),
        embedding_model=settings.embedding_model,
        total_chunks=len(rows),
        products={
            p: ProductStats(chunk_count=c) for p, c in product_counts.items()
        },
    )
    save_manifest(kb_path / "manifest.json", manifest)

    capsules = {
        p: ARCHITECTURE_FACTS.get(p.upper(), {}).get("en", p)
        for p in product_counts
    }
    (kb_path / "product_capsules.json").write_text(
        json.dumps(capsules, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest
