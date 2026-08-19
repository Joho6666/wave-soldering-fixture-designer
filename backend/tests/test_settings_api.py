import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings, get_masked_api_key

client = TestClient(app)


def test_get_masked_api_key():
    assert get_masked_api_key("") == ""
    assert get_masked_api_key("sk-1234567890abcdef") == "sk-****cdef"
    assert get_masked_api_key("short") == "****"
    assert get_masked_api_key("mycustomkey12345") == "my****2345"


def test_get_and_put_ai_settings():
    # Save old settings
    old_enabled = settings.AI_ENABLED
    old_provider = settings.AI_PROVIDER
    old_base_url = settings.AI_BASE_URL
    old_model = settings.AI_MODEL
    old_key = settings.AI_API_KEY
    old_timeout = settings.AI_TIMEOUT_MS

    try:
        # GET default/current settings
        res = client.get("/api/settings/ai")
        assert res.status_code == 200
        data = res.json()
        assert "aiEnabled" in data
        assert "aiApiKeyMasked" in data

        # PUT update settings with new key
        update_payload = {
            "aiEnabled": True,
            "aiProvider": "openai_compatible",
            "aiBaseUrl": "https://api.example.com/v1",
            "aiModel": "gpt-4o-mini",
            "aiApiKey": "sk-test1234567890abcdef",
            "aiTimeoutMs": 8000,
        }
        put_res = client.put("/api/settings/ai", json=update_payload)
        assert put_res.status_code == 200
        updated = put_res.json()
        assert updated["aiEnabled"] is True
        assert updated["aiBaseUrl"] == "https://api.example.com/v1"
        assert updated["aiModel"] == "gpt-4o-mini"
        assert updated["aiApiKeyMasked"] == "sk-****cdef"
        assert updated["aiTimeoutMs"] == 8000
        assert settings.AI_API_KEY == "sk-test1234567890abcdef"

        # PUT update without supplying new key preserves old key
        update_no_key = {
            "aiEnabled": True,
            "aiProvider": "openai_compatible",
            "aiBaseUrl": "https://api.example.com/v1",
            "aiModel": "gpt-4o",
            "aiApiKey": "",
            "aiTimeoutMs": 8000,
        }
        put_res2 = client.put("/api/settings/ai", json=update_no_key)
        assert put_res2.status_code == 200
        updated2 = put_res2.json()
        assert updated2["aiModel"] == "gpt-4o"
        assert updated2["aiApiKeyMasked"] == "sk-****cdef"
        assert settings.AI_API_KEY == "sk-test1234567890abcdef"

    finally:
        # Restore old settings
        settings.AI_ENABLED = old_enabled
        settings.AI_PROVIDER = old_provider
        settings.AI_BASE_URL = old_base_url
        settings.AI_MODEL = old_model
        settings.AI_API_KEY = old_key
        settings.AI_TIMEOUT_MS = old_timeout


def test_test_ai_settings_unconfigured():
    old_key, old_model = settings.AI_API_KEY, settings.AI_MODEL
    try:
        settings.AI_API_KEY = ""
        settings.AI_MODEL = ""
        res = client.post("/api/settings/ai/test")
        assert res.status_code == 200
        assert res.json()["ok"] is False
        assert "API Key" in res.json()["message"]
    finally:
        settings.AI_API_KEY = old_key
        settings.AI_MODEL = old_model
