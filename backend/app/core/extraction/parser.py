"""Document parsing wrapper (Docling for PDF/DOCX)."""

from __future__ import annotations

from pathlib import Path


def parse_document(path: Path) -> str:
    """Extract plain/markdown text from PDF or DOCX via Docling."""
    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".docx", ".doc"}:
        raise ValueError(f"Unsupported format: {suffix}")

    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(path))
        return result.document.export_to_markdown()
    except ImportError:
        return path.read_text(encoding="utf-8", errors="replace")


def parse_upload_bytes(data: bytes, filename: str) -> str:
    import tempfile

    suffix = Path(filename).suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        if suffix.lower() in {".pdf", ".docx", ".doc"}:
            return parse_document(tmp_path)
        return tmp_path.read_text(encoding="utf-8", errors="replace")
    finally:
        tmp_path.unlink(missing_ok=True)
