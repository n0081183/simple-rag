# ADR 003: LLM strategy — Ollama default, API opt-in

## Status

Accepted (Milestone 0)

## Context

The app must work **offline** after KB sync, with quality sufficient for expert-facing reports. v3 validated **Qwen 3 8B (Q4_K_M)** via Ollama for Polish SIWZ text. Some users want higher quality via cloud API.

## Decision

| Use case | Default | Premium (settings toggle) |
|----------|---------|---------------------------|
| Block validation (extraction) | Ollama / Qwen3 8B | Anthropic Claude Sonnet |
| Requirement verification | Ollama / Qwen3 8B | Anthropic Claude Sonnet |
| Product capsule generation (KB build) | Ollama on pod or skip | N/A on pod (template from docs) |

**Structured output**: Pydantic models + JSON schema in prompts; Ollama `format` JSON when supported, else parse with `instructor` or strict retry.

## Rationale

1. Offline-first matches presales laptops at customer sites.
2. Dual-mode is a **settings switch**, not a fork — `LLMProvider` protocol with `OllamaProvider` and `AnthropicProvider`.
3. API keys in keychain (`siwz-rag-lite/anthropic`), never `.env` in repo.

## Prompt policy (inherited from v3, extended)

- 4-step chain-of-thought for verification
- Hard rule: no evidence → `UNCLEAR`
- Extraction: per-block JSON schema (`is_requirement`, `split_into`, `reason_if_not`)

## Consequences

- `backend/app/core/verification/llm_local.py`, `llm_api.py`
- Settings UI: “Quality: Local (offline) / Cloud API”
- `make preflight` checks Ollama reachability and model pull
