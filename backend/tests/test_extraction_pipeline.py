from app.core.extraction.pipeline import ExtractionPipeline


import os

os.environ.setdefault("SIWZ_SKIP_ML", "1")


def test_extraction_heuristic():
    text = """
    Wymagania:
    - Dostawca musi zapewnić agenta EDR na Windows 10.
    - System powinien wspierać integrację z SIEM.
    """
    pipeline = ExtractionPipeline(language="pl", use_llm=False)
    result = pipeline.run(text)
    assert result.status == "completed"
    assert len(result.requirements) >= 1


def test_extraction_auto_detect_suggestions():
    text = """
    Wymagania:
    - Agent EDR na Windows, integracja WildFire i NGFW.
    - Endpoint detection and response w środowisku korporacyjnym.
    """
    pipeline = ExtractionPipeline(language="pl", use_llm=False)
    result = pipeline.run(text, auto_detect=True)
    assert result.auto_detect_warning is True
    assert len(result.product_suggestions) >= 1
    assert result.product_suggestions[0].product == "xdr"
