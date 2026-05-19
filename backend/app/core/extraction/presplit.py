"""Heuristic pre-split of SIWZ/RFP documents (deterministic, no LLM).

Ported patterns from siwz-rag-v3 batch_processor.pre_split_requirements.
"""

from __future__ import annotations

import re

# Modal / obligation verbs (PL + EN)
_REQUIREMENT_PATTERNS = re.compile(
    r"\b("
    r"musi|muszą|powinien|powinna|powinni|powinny|"
    r"wymaga(?:\s+się)?|"
    r"shall|must|should|required|requirements?"
    r")\b",
    re.IGNORECASE,
)

_INTRO_PATTERNS = re.compile(
    r"^(?:wprowadzenie|zakres|definicje|spis treści|table of contents|"
    r"przedmiot zamówienia|opis przedmiotu)\b",
    re.IGNORECASE,
)

_BULLET_RE = re.compile(r"^[\s]*(?:[-•●▪◦]|\d+[\.\)]|[a-z][\.\)])\s+", re.MULTILINE)
_HEADER_RE = re.compile(r"^[\s]*[A-ZĄĆĘŁŃÓŚŹŻ0-9][^.]{2,80}:?\s*$", re.MULTILINE)


def _has_requirement_keyword(text: str) -> bool:
    return bool(_REQUIREMENT_PATTERNS.search(text))


def _is_intro(text: str) -> bool:
    first = text.strip().split("\n")[0][:120]
    return bool(_INTRO_PATTERNS.match(first))


def _is_continuation(line: str) -> bool:
    stripped = line.strip().lower()
    return stripped.startswith(("ww.", "tj.", "czyli", "w tym", "do ww.", "nie zalicza"))


def pre_split_blocks(doc_text: str, min_block_len: int = 15) -> list[str]:
    """Split document into candidate blocks (~1–5 sentences each)."""
    if not doc_text or not doc_text.strip():
        return []

    lines = doc_text.splitlines()
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        block = " ".join(s.strip() for s in current if s.strip())
        if len(block) >= min_block_len:
            blocks.append(block)
        current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue

        is_bullet = bool(_BULLET_RE.match(stripped))
        is_header = bool(_HEADER_RE.match(stripped)) and stripped.endswith(":")

        if is_header and current:
            flush()
            current = [stripped]
            continue

        if is_bullet and current and not _is_continuation(stripped):
            prev = " ".join(current)
            if _has_requirement_keyword(prev) or len(prev) > 200:
                flush()
            current.append(stripped)
            continue

        if _is_continuation(stripped) and current:
            current.append(stripped)
            continue

        if _has_requirement_keyword(stripped) and current:
            prev_text = " ".join(current)
            if _has_requirement_keyword(prev_text) and not _is_continuation(stripped):
                flush()

        current.append(stripped)

    flush()

    # Sentence-level split for long paragraphs without bullets
    refined: list[str] = []
    for block in blocks:
        if len(block) > 800 and ". " in block:
            sentences = re.split(r"(?<=[.!?])\s+", block)
            chunk: list[str] = []
            for sent in sentences:
                chunk.append(sent)
                joined = " ".join(chunk)
                if _has_requirement_keyword(joined) and len(joined) > 40:
                    refined.append(joined)
                    chunk = []
            if chunk:
                tail = " ".join(chunk)
                if len(tail) >= min_block_len:
                    refined.append(tail)
        else:
            refined.append(block)

    return refined
