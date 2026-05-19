from app.core.extraction.pipeline import ExtractionPipeline


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
