from app.core.config import settings, update_runtime_ai_settings, get_masked_api_key


def test_masked_key_does_not_overwrite_real_key():
    settings.AI_API_KEY = "sk-real-secret-key-123456"
    masked = get_masked_api_key(settings.AI_API_KEY)
    assert "****" in masked

    # 尝试用脱敏字符串更新
    res = update_runtime_ai_settings(
        ai_enabled=True,
        ai_api_key=masked,
    )
    # 真实密钥未被破坏
    assert settings.AI_API_KEY == "sk-real-secret-key-123456"
    assert res["aiApiKeyMasked"] == masked


def test_valid_new_key_updates_properly():
    settings.AI_API_KEY = "sk-old-key-1111"
    update_runtime_ai_settings(
        ai_enabled=True,
        ai_api_key="sk-brand-new-key-9999",
    )
    assert settings.AI_API_KEY == "sk-brand-new-key-9999"
