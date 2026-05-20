import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings, save_user_config
from app.main import app

client = TestClient(app)


def test_get_llm_settings():
    res = client.get("/api/settings/llm")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] in ("ollama", "anthropic")
    assert "ollama_model" in data


def test_patch_llm_provider_ollama(tmp_path, monkeypatch):
    cfg_path = tmp_path / "user_config.json"
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()

    save_user_config({"llm_provider": "anthropic"})
    res = client.patch("/api/settings/llm", json={"provider": "ollama"})
    assert res.status_code == 200
    assert res.json()["provider"] == "ollama"
    assert json.loads(cfg_path.read_text())["llm_provider"] == "ollama"
