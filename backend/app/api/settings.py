"""Application settings API (secrets via keychain handles only)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings, load_user_config, save_user_config
from app.infra import keychain

router = APIRouter(prefix="/settings", tags=["settings"])


class SecretSetRequest(BaseModel):
    name: str
    value: str


class LLMSettingsUpdate(BaseModel):
    provider: str | None = Field(default=None, pattern="^(ollama|anthropic)$")
    extraction_use_llm: bool | None = None


class LLMSettingsResponse(BaseModel):
    provider: str
    ollama_model: str
    ollama_base_url: str
    extraction_use_llm: bool
    has_anthropic_key: bool
    has_runpod_key: bool
    has_openai_key: bool = False


@router.get("/llm", response_model=LLMSettingsResponse)
def get_llm_settings():
    s = get_settings()
    return LLMSettingsResponse(
        provider=s.llm_provider,
        ollama_model=s.ollama_model,
        ollama_base_url=s.ollama_base_url,
        extraction_use_llm=s.extraction_use_llm,
        has_anthropic_key=keychain.has_secret("anthropic_api_key"),
        has_runpod_key=keychain.has_secret("runpod_api_key"),
        has_openai_key=keychain.has_secret("openai_api_key"),
    )


@router.patch("/llm", response_model=LLMSettingsResponse)
def update_llm_settings(body: LLMSettingsUpdate):
    if body.provider is not None and body.provider == "anthropic" and not keychain.has_secret(
        "anthropic_api_key"
    ):
        raise HTTPException(
            400,
            "Anthropic API key not configured. Add it in Settings first.",
        )
    cfg = load_user_config()
    if body.provider is not None:
        cfg["llm_provider"] = body.provider
    if body.extraction_use_llm is not None:
        cfg["extraction_use_llm"] = body.extraction_use_llm
    save_user_config(cfg)
    get_settings.cache_clear()
    return get_llm_settings()


@router.post("/secrets")
def set_secret(body: SecretSetRequest):
    allowed = {"runpod_api_key", "anthropic_api_key", "openai_api_key"}
    if body.name not in allowed:
        raise HTTPException(400, f"Unknown secret name: {body.name}")
    keychain.set_secret(body.name, body.value)
    return {"ok": True, "name": body.name}


@router.delete("/secrets/{name}")
def delete_secret(name: str):
    keychain.delete_secret(name)
    return {"ok": True}
