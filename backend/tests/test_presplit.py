from app.core.extraction.presplit import pre_split_blocks


def test_presplit_modal_verb():
    text = """
    Wymagania funkcjonalne:
    - Dostawca musi zapewnić agenta EDR na Windows 10.
    - System powinien wspierać integrację z SIEM.
    """
    blocks = pre_split_blocks(text)
    assert len(blocks) >= 1
    assert any("musi" in b.lower() or "powinien" in b.lower() for b in blocks)


def test_presplit_empty():
    assert pre_split_blocks("") == []
