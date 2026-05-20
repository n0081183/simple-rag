from app.core.extraction.validator import BlockValidator


def test_llm_empty_response_falls_back_heuristic():
    class StubLLM:
        def complete_json(self, *args, **kwargs):
            return {}

        def complete_text(self, *args, **kwargs):
            return ""

    v = BlockValidator(language="pl", use_llm=True)
    v._llm = StubLLM()  # type: ignore[assignment]
    block = "Dostawca musi zapewnić agenta EDR na wszystkich stacjach roboczych."
    reqs = v.validate(block, 0)
    assert len(reqs) >= 1
    assert "musi" in reqs[0].text.lower()
