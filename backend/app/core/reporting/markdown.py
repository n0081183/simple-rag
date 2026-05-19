"""Markdown report export."""

from __future__ import annotations

from app.core.verification.schemas import VerificationResult, Verdict

_VERDICT_ICON = {
    Verdict.MET: "✅",
    Verdict.PARTIAL: "⚠️",
    Verdict.NOT_MET: "❌",
    Verdict.UNCLEAR: "❓",
}


def export_markdown(
    results: list[VerificationResult],
    title: str = "SIWZ Verification Report",
    language: str = "pl",
    auto_detect_warning: bool = False,
) -> str:
    lines = [f"# {title}", ""]
    if auto_detect_warning:
        msg = (
            "> **Automatyczne dopasowanie produktu — wymaga weryfikacji przez specjalistę Cortex.**"
            if language == "pl"
            else "> **Product auto-detected — requires Cortex expert verification.**"
        )
        lines.extend([msg, ""])

    for i, r in enumerate(results, 1):
        icon = _VERDICT_ICON.get(r.verdict, "❓")
        lines.append(f"## {i}. {icon} {r.verdict.value} ({r.confidence.value})")
        lines.append("")
        lines.append(r.requirement_text)
        lines.append("")
        for step in r.reasoning_steps:
            lines.append(f"- {step}")
        if r.evidence:
            lines.append("")
            lines.append("### Evidence" if language == "en" else "### Dowody")
            for ev in r.evidence:
                lines.append(f"- [{ev.source_file}]({ev.topic_url}): {ev.quote[:200]}...")
        lines.append("")
    return "\n".join(lines)
