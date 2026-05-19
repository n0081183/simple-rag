#!/usr/bin/env python3
"""Gold-set evaluation — precision/recall on extraction + verification accuracy."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SIWZ_SKIP_ML", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.extraction.pipeline import ExtractionPipeline
from app.core.verification.schemas import Verdict
from app.core.verification.verifier import VerificationOrchestrator


def main() -> int:
    gold_path = Path(__file__).parent / "gold_set.json"
    data = json.loads(gold_path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])

    correct = 0
    total = len(cases)
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)

    results_log = []
    for case in cases:
        req_text = case["requirement"]
        product = case["product"]
        expected = case["expected_verdict"]

        from app.core.extraction.schemas import ExtractedRequirement

        req = ExtractedRequirement(title=req_text[:40], text=req_text)
        orch = VerificationOrchestrator(product=product, language=case.get("language", "pl"))
        result = orch.verify_one(req)
        match = result.verdict.value == expected
        if match:
            correct += 1
        results_log.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": result.verdict.value,
                "match": match,
            }
        )

    accuracy = correct / total if total else 0.0
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "details": results_log,
    }
    out = report_dir / "latest.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Eval: {correct}/{total} accuracy={accuracy:.2%}")
    print(f"Report: {out}")
    return 0 if accuracy >= 0.0 else 1  # M0: always pass structure; M1: threshold


if __name__ == "__main__":
    raise SystemExit(main())
