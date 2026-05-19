"""XLSX report export."""

from __future__ import annotations

from io import BytesIO

from app.core.verification.schemas import VerificationResult


def export_xlsx(results: list[VerificationResult]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Requirements"
    ws.append(
        [
            "ID",
            "Requirement",
            "Verdict",
            "Confidence",
            "Evidence Count",
            "Caveats",
        ]
    )
    for r in results:
        ws.append(
            [
                r.requirement_id,
                r.requirement_text[:500],
                r.verdict.value,
                r.confidence.value,
                len(r.evidence),
                r.caveats or "",
            ]
        )
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
