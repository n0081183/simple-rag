"""Markdown report export."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.reporting.anonymizer import anonymize_results
from app.core.verification.schemas import VerificationResult, Verdict

_VERDICT_ICON = {
    Verdict.MET: "MET",
    Verdict.PARTIAL: "PARTIAL",
    Verdict.NOT_MET: "NOT_MET",
    Verdict.UNCLEAR: "UNCLEAR",
}

_LABELS = {
    "pl": {
        "title": "Raport weryfikacji wymagań SIWZ",
        "generated": "Wygenerowano",
        "product": "Produkt",
        "summary": "Podsumowanie",
        "auto_warn": "> **Automatyczne dopasowanie produktu — wymaga weryfikacji przez specjalistę Cortex.**",
        "evidence": "Dowody",
        "reasoning": "Uzasadnienie",
    },
    "en": {
        "title": "SIWZ Requirements Verification Report",
        "generated": "Generated",
        "product": "Product",
        "summary": "Summary",
        "auto_warn": "> **Product auto-detected — requires Cortex expert verification.**",
        "evidence": "Evidence",
        "reasoning": "Reasoning",
    },
}


def export_markdown(
    results: list[VerificationResult],
    title: str | None = None,
    language: str = "pl",
    auto_detect_warning: bool = False,
    product: str | None = None,
    anonymize: bool = False,
) -> str:
    L = _LABELS.get(language, _LABELS["en"])
    if anonymize:
        results = anonymize_results(results)

    lines = [
        f"# {title or L['title']}",
        "",
        f"*{L['generated']}:* {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if product:
        lines.append(f"*{L['product']}:* {product}")
    lines.append("")

    if auto_detect_warning:
        lines.extend([L["auto_warn"], ""])

    counts = {v: 0 for v in Verdict}
    for r in results:
        counts[r.verdict] += 1
    lines.append(f"## {L['summary']}")
    lines.append("")
    lines.append("| Verdict | Count |")
    lines.append("| --- | --- |")
    for v in Verdict:
        lines.append(f"| {v.value} | {counts[v]} |")
    lines.append("")

    for i, r in enumerate(results, 1):
        icon = _VERDICT_ICON.get(r.verdict, "?")
        lines.append(f"## {i}. {icon} ({r.confidence.value})")
        lines.append("")
        lines.append(r.requirement_text)
        lines.append("")
        if r.reasoning_steps:
            lines.append(f"### {L['reasoning']}")
            for step in r.reasoning_steps:
                lines.append(f"- {step}")
        if r.evidence:
            lines.append("")
            lines.append(f"### {L['evidence']}")
            for ev in r.evidence:
                lines.append(f"- [{ev.source_file}]({ev.topic_url}): {ev.quote[:300]}")
        if r.caveats:
            lines.append(f"\n*Caveats:* {r.caveats}")
        lines.append("")
    return "\n".join(lines)
