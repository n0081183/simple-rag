#!/usr/bin/env python3
"""Gold-set evaluation — verdict accuracy with seed KB."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SIWZ_SKIP_ML", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings
from app.core.extraction.schemas import ExtractedRequirement
from app.core.kb.ingest import build_seed_kb
from app.core.extraction.pipeline import ExtractionPipeline
from app.core.extraction.presplit import pre_split_blocks
from app.core.verification.verifier import VerificationOrchestrator


def main() -> int:
    gold_path = Path(__file__).parent / "gold_set.json"
    data = json.loads(gold_path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])

    settings = get_settings()
    build_seed_kb(settings.kb_active_path, skip_ml=True)

    # Extraction smoke: single combined doc
    sample_doc = "\n\n".join(c["requirement"] for c in cases[:5])
    blocks = pre_split_blocks(sample_doc)
    pipeline = ExtractionPipeline(language="pl", use_llm=False)
    ext = pipeline.run(sample_doc)
    extraction_recall = min(1.0, len(ext.requirements) / max(len(blocks), 1))

    correct = 0
    total = len(cases)
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    details = []

    for case in cases:
        req = ExtractedRequirement(title=case["id"], text=case["requirement"])
        orch = VerificationOrchestrator(product=case["product"], language=case.get("language", "pl"))
        result = orch.verify_one(req)
        expected = case["expected_verdict"]
        match = result.verdict.value == expected
        if match:
            correct += 1
        details.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": result.verdict.value,
                "confidence": result.confidence.value,
                "evidence_count": len(result.evidence),
                "match": match,
            }
        )

    accuracy = correct / total if total else 0.0
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "extraction_blocks": len(blocks),
        "extraction_requirements": len(ext.requirements),
        "extraction_recall_proxy": extraction_recall,
        "details": details,
    }
    out = report_dir / "latest.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Verdict accuracy: {correct}/{total} ({accuracy:.1%})")
    print(f"Extraction proxy recall: {extraction_recall:.1%} ({len(ext.requirements)} reqs / {len(blocks)} blocks)")
    print(f"Report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
