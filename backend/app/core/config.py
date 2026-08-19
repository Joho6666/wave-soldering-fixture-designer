"""
Application Configuration
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用设置"""
    
    # Application
    APP_NAME: str = "WAVE-FIXTURE AI Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG_GEOMETRY: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./fixture_ai.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:3002", 
        "http://localhost:3003", 
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:3005",
    ]
    
    # API
    API_V1_PREFIX: str = "/api"

    # Server-side OpenAI-compatible AI provider
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "openai_compatible"
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = ""
    AI_TIMEOUT_MS: int = 10000
    AI_MAX_INPUT_CHARS: int = 4000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()


def get_masked_api_key(key: str) -> str:
    """将 API Key 脱敏展示"""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    if key.startswith("sk-"):
        return f"sk-****{key[-4:]}"
    return f"{key[:2]}****{key[-4:]}"


def save_ai_settings_to_env(env_path: str = ".env"):
    """持久化 AI 设置到 .env 文件"""
    updates = {
        "AI_ENABLED": "true" if settings.AI_ENABLED else "false",
        "AI_PROVIDER": settings.AI_PROVIDER,
        "AI_API_KEY": settings.AI_API_KEY,
        "AI_BASE_URL": settings.AI_BASE_URL,
        "AI_MODEL": settings.AI_MODEL,
        "AI_TIMEOUT_MS": str(settings.AI_TIMEOUT_MS),
    }
    
    lines = []
    found_keys = set()
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#"):
                    k, _ = stripped.split("=", 1)
                    k = k.strip()
                    if k in updates:
                        lines.append(f"{k}={updates[k]}\n")
                        found_keys.add(k)
                        continue
                lines.append(line)
                
    for k, v in updates.items():
        if k not in found_keys:
            lines.append(f"{k}={v}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def update_runtime_ai_settings(
    ai_enabled: bool,
    ai_provider: Optional[str] = None,
    ai_base_url: Optional[str] = None,
    ai_model: Optional[str] = None,
    ai_api_key: Optional[str] = None,
    ai_timeout_ms: Optional[int] = None,
) -> dict:
    """在运行时更新 AI 设置并保存"""
    settings.AI_ENABLED = ai_enabled
    if ai_provider is not None:
        settings.AI_PROVIDER = ai_provider
    if ai_base_url is not None:
        settings.AI_BASE_URL = ai_base_url
    if ai_model is not None:
        settings.AI_MODEL = ai_model
    if ai_api_key is not None and ai_api_key.strip():
        settings.AI_API_KEY = ai_api_key.strip()
    if ai_timeout_ms is not None:
        settings.AI_TIMEOUT_MS = ai_timeout_ms
        
    try:
        save_ai_settings_to_env()
    except Exception:
        pass
        
    return {
        "aiEnabled": settings.AI_ENABLED,
        "aiProvider": settings.AI_PROVIDER,
        "aiBaseUrl": settings.AI_BASE_URL,
        "aiModel": settings.AI_MODEL,
        "aiApiKeyMasked": get_masked_api_key(settings.AI_API_KEY),
        "aiTimeoutMs": settings.AI_TIMEOUT_MS,
    }


SOFTWARE_VERSION = "0.4.0"
ALGORITHM_VERSION = "fixture-engine-0.4.0"
RULE_PROFILE_VERSION = "1.0.0"
