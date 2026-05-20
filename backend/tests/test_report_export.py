from app.core.reporting.anonymizer import anonymize_text
from app.core.reporting.docx import export_docx
from app.core.reporting.markdown import export_markdown
from app.core.reporting.xlsx import export_xlsx
from app.core.verification.schemas import Confidence, EvidenceItem, VerificationResult, Verdict


def _sample_result() -> VerificationResult:
    return VerificationResult(
        requirement_id="req-1",
        requirement_text="Cortex XDR must support EDR agents.",
        verdict=Verdict.PARTIAL,
        confidence=Confidence.MEDIUM,
        reasoning_steps=["Step one mentions Palo Alto Networks."],
        evidence=[
            EvidenceItem(
                source_file="xdr-admin.pdf",
                topic_url="https://docs.example/xdr",
                quote="Cortex XDR agent deployment guide.",
                relevance="high",
            )
        ],
        caveats="Review licensing.",
    )


def test_anonymize_text():
    out = anonymize_text("Cortex XDR from Palo Alto Networks")
    assert "Cortex XDR" not in out
    assert "Palo Alto" not in out


def test_export_markdown_bilingual():
    r = _sample_result()
    pl = export_markdown([r], language="pl", product="xdr", anonymize=True)
    en = export_markdown([r], language="en", product="xdr")
    assert "Podsumowanie" in pl
    assert "Summary" in en


def test_export_docx_and_xlsx_smoke():
    r = _sample_result()
    docx = export_docx([r], language="pl", product="xdr", auto_detect_warning=True)
    xlsx = export_xlsx([r], language="en", product="xdr", anonymize=True)
    assert docx[:2] == b"PK"
    assert xlsx[:2] == b"PK"
