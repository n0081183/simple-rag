"""Architecture facts per Cortex product (PL/EN) — extended for Cloud & AgentiX."""

from __future__ import annotations

ARCHITECTURE_FACTS: dict[str, dict[str, str]] = {
    "XDR": {
        "pl": (
            "Cortex XDR — Extended Detection and Response. SaaS lub on-prem. "
            "Agent na Windows, macOS, Linux, Android, iOS. Broker VM, WildFire, integracja NGFW."
        ),
        "en": (
            "Cortex XDR — Extended Detection and Response. SaaS or on-prem. "
            "Agent on Windows, macOS, Linux, Android, iOS. Broker VM, WildFire, NGFW integration."
        ),
    },
    "XSIAM": {
        "pl": (
            "Cortex XSIAM — SIEM/SOAR/XDR SaaS. Broker VM opcjonalnie on-prem. "
            "Data Lake, XDR Agent, WildFire, Copilot, playbooki SOAR."
        ),
        "en": (
            "Cortex XSIAM — SIEM/SOAR/XDR SaaS. Optional on-prem Broker VM. "
            "Data Lake, XDR Agent, WildFire, Copilot, SOAR playbooks."
        ),
    },
    "XSOAR": {
        "pl": (
            "Cortex XSOAR — SOAR on-premises lub cloud. Playbooki, 700+ integracji, War Room."
        ),
        "en": (
            "Cortex XSOAR — SOAR on-prem or cloud. Playbooks, 700+ integrations, War Room."
        ),
    },
    "XPANSE": {
        "pl": (
            "Cortex XPANSE — Attack Surface Management SaaS. Skan IPv4/IPv6, ASM, CVE."
        ),
        "en": (
            "Cortex XPANSE — Attack Surface Management SaaS. IPv4/IPv6 scan, ASM, CVE."
        ),
    },
    "CORTEX_CLOUD": {
        "pl": (
            "Cortex Cloud — unified cloud security (CNAPP/CSPM/CWPP). "
            "Prisma Cloud capabilities, posture, workload protection, CI/CD scanning."
        ),
        "en": (
            "Cortex Cloud — unified cloud security (CNAPP/CSPM/CWPP). "
            "Prisma Cloud capabilities, posture, workload protection, CI/CD scanning."
        ),
    },
    "AGENTIX": {
        "pl": (
            "Cortex AgentiX — AI agents for security operations. "
            "Automatyzacja analiz, integracja z XSIAM/XSOAR, Copilot-style workflows."
        ),
        "en": (
            "Cortex AgentiX — AI agents for security operations. "
            "Automation of analysis, integration with XSIAM/XSOAR, Copilot-style workflows."
        ),
    },
}


def get_architecture_facts(product: str, language: str = "pl") -> str:
    key = product.upper().replace("-", "_")
    facts = ARCHITECTURE_FACTS.get(key, {})
    return facts.get(language, facts.get("en", ""))


def get_domain_knowledge_prompt(product: str | None, language: str = "pl") -> str:
    if not product:
        return ""
    facts = get_architecture_facts(product, language)
    if not facts:
        return ""
    header = "FAKTY PRODUKTOWE:" if language == "pl" else "PRODUCT FACTS:"
    return f"{header}\n{facts}"
