"""Prompts for per-block requirement validation."""

BLOCK_VALIDATE_SCHEMA_HINT = """JSON schema:
{
  "is_requirement": boolean,
  "reason_if_not": string | null,
  "split_into": [string],
  "title": string | null,
  "category": "functional" | "non_functional" | "compatibility" | "security" | "commercial" | "other",
  "priority": "mandatory" | "scored" | "optional" | "unknown"
}"""


def block_validate_system(language: str) -> str:
    if language == "pl":
        return f"""Jesteś ekspertem od dokumentów SIWZ/RFP/OPZ.
Dostajesz JEDEN blok tekstu (~1-5 zdań). Odpowiedz WYŁĄCZNIE jako JSON.

Zasady:
- is_requirement=true gdy blok zawiera wymaganie techniczne (musi, wymaga się, shall, must, parametry liczbowe).
- is_requirement=false dla: nagłówków, danych zamawiającego, klauzul prawnych, wprowadzeń — podaj reason_if_not.
- split_into: lista treści wymagań (oryginalny tekst, bez parafrazy). Jedno lub więcej.
- Jeśli wymaganie + wyjątek ("Do ww. nie zalicza się") — jeden element split_into.
- title: krótki tytuł 5-8 słów.
- category i priority jeśli da się wywnioskować z tekstu.

{BLOCK_VALIDATE_SCHEMA_HINT}"""
    return f"""You are an RFP/ITT document expert.
You receive ONE text block (~1-5 sentences). Respond ONLY as JSON.

Rules:
- is_requirement=true for technical requirements (must, shall, numeric parameters).
- is_requirement=false for headers, legal clauses, introductions — set reason_if_not.
- split_into: list of requirement texts (original wording). One or more.
- Keep requirement + exception in one split_into entry when linked.
- title: short 5-8 word title.

{BLOCK_VALIDATE_SCHEMA_HINT}"""
