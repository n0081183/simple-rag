"""Application settings API (secrets via keychain handles only)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.infra import keychain

router = APIRouter(prefix="/settings", tags=["settings"])


class SecretSetRequest(BaseModel):
    name: str
    value: str


class LLMSettingsResponse(BaseModel):
    provider: str
    ollama_model: str
    ollama_base_url: str
    has_anthropic_key: bool
    has_runpod_key: bool


@router.get("/llm", response_model=LLMSettingsResponse)
def get_llm_settings():
    s = get_settings()
    return LLMSettingsResponse(
        provider=s.llm_provider,
        ollama_model=s.ollama_model,
        ollama_base_url=s.ollama_base_url,
        has_anthropic_key=keychain.has_secret("anthropic_api_key"),
        has_runpod_key=keychain.has_secret("runpod_api_key"),
    )


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
