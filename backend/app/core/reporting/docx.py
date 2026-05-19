"""DOCX report export (stub — full formatting in Milestone 3)."""

from __future__ import annotations

from io import BytesIO

from app.core.reporting.markdown import export_markdown
from app.core.verification.schemas import VerificationResult


def export_docx(results: list[VerificationResult], title: str = "SIWZ Report", **kwargs) -> bytes:
    try:
        from docx import Document

        doc = Document()
        doc.add_heading(title, 0)
        md = export_markdown(results, title=title, **kwargs)
        for line in md.splitlines():
            if line.startswith("# "):
                doc.add_heading(line[2:], level=1)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.strip():
                doc.add_paragraph(line)
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
    except ImportError:
        return export_markdown(results, title=title, **kwargs).encode("utf-8")
