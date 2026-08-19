"""
AI 设置与配置管理 API
"""
from __future__ import annotations

from typing import Optional
import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings, get_masked_api_key, update_runtime_ai_settings

router = APIRouter()


class AISettingsResponse(BaseModel):
    aiEnabled: bool = Field(..., description="是否启用 AI 助手")
    aiProvider: str = Field(..., description="AI 服务商")
    aiBaseUrl: str = Field(..., description="API Base URL")
    aiModel: str = Field(..., description="模型名称")
    aiApiKeyMasked: str = Field(..., description="脱敏后的 API Key")
    aiTimeoutMs: int = Field(..., description="请求超时时间 (ms)")


class AISettingsUpdate(BaseModel):
    aiEnabled: bool
    aiProvider: Optional[str] = "openai_compatible"
    aiBaseUrl: Optional[str] = "https://api.openai.com/v1"
    aiModel: Optional[str] = ""
    aiApiKey: Optional[str] = None
    aiTimeoutMs: Optional[int] = 10000


class AITestRequest(BaseModel):
    aiEnabled: Optional[bool] = None
    aiProvider: Optional[str] = "openai_compatible"
    aiBaseUrl: Optional[str] = None
    aiModel: Optional[str] = None
    aiApiKey: Optional[str] = None
    aiTimeoutMs: Optional[int] = None


class AITestResponse(BaseModel):
    ok: bool
    message: str


@router.get("/settings/ai", response_model=AISettingsResponse)
async def get_ai_settings():
    """获取当前 AI 配置（API Key 掩码返回）"""
    return AISettingsResponse(
        aiEnabled=settings.AI_ENABLED,
        aiProvider=settings.AI_PROVIDER,
        aiBaseUrl=settings.AI_BASE_URL,
        aiModel=settings.AI_MODEL,
        aiApiKeyMasked=get_masked_api_key(settings.AI_API_KEY),
        aiTimeoutMs=settings.AI_TIMEOUT_MS,
    )


@router.put("/settings/ai", response_model=AISettingsResponse)
async def update_ai_settings(payload: AISettingsUpdate):
    """更新 AI 配置（运行时热更新并持久化）"""
    res = update_runtime_ai_settings(
        ai_enabled=payload.aiEnabled,
        ai_provider=payload.aiProvider,
        ai_base_url=payload.aiBaseUrl,
        ai_model=payload.aiModel,
        ai_api_key=payload.aiApiKey,
        ai_timeout_ms=payload.aiTimeoutMs,
    )
    return AISettingsResponse(**res)


@router.post("/settings/ai/test", response_model=AITestResponse)
async def test_ai_settings(payload: Optional[AITestRequest] = None):
    """测试 AI API 连通性"""
    api_key = (payload.aiApiKey if payload and payload.aiApiKey else settings.AI_API_KEY).strip()
    model = (payload.aiModel if payload and payload.aiModel else settings.AI_MODEL).strip()
    base_url = (payload.aiBaseUrl if payload and payload.aiBaseUrl else settings.AI_BASE_URL).strip().rstrip("/")
    timeout_ms = payload.aiTimeoutMs if payload and payload.aiTimeoutMs else settings.AI_TIMEOUT_MS

    if not api_key:
        return AITestResponse(ok=False, message="未配置 API Key，请先填入 API Key。")
    if not model:
        return AITestResponse(ok=False, message="未配置 Model 名称，请先指定模型。")
    if not base_url:
        return AITestResponse(ok=False, message="未配置接口地址 (Base URL)。")
    
    # 构造请求端点
    if base_url.endswith("/chat/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"

    test_payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "ping"}
        ],
        "max_tokens": 5,
    }
    try:
        timeout_sec = min(max(timeout_ms / 1000, 2.0), 15.0)
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=test_payload,
            )
            # 如果是 404 且 base_url 不含 /v1，尝试 /v1/chat/completions
            if resp.status_code == 404 and not base_url.endswith("/v1"):
                v1_url = f"{base_url}/v1/chat/completions"
                resp = await client.post(
                    v1_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=test_payload,
                )
            
            if resp.status_code == 200:
                return AITestResponse(ok=True, message=f"连接成功！模型 [{model}] 响应正常。")
            else:
                err_text = resp.text[:200]
                return AITestResponse(ok=False, message=f"接口返回 HTTP {resp.status_code}: {err_text}")
    except httpx.TimeoutException:
        return AITestResponse(ok=False, message=f"连接超时 ({timeout_sec:.0f}s)，请检查 Base URL 是否可正常访问。")
    except Exception as exc:
        return AITestResponse(ok=False, message=f"连接失败: {str(exc)}")
