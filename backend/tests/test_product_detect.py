import os

os.environ.setdefault("SIWZ_SKIP_ML", "1")

from app.core.retrieval.product_match import detect_products


def test_detect_products_lexical_xdr():
    corpus = """
    Wymagania dotyczą agenta EDR na stacjach Windows oraz integracji z NGFW i WildFire.
    System musi obsługiwać endpoint detection and response.
    """
    ranked = detect_products(corpus, top_n=3)
    assert ranked
    assert ranked[0].product == "xdr"
    assert ranked[0].lexical_score > 0


def test_detect_products_empty():
    assert detect_products("") == []
    assert detect_products("   ") == []
