"""OpenAI-compatible provider. Credentials stay on the FastAPI server."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import settings
from app.models.ai_schemas import (
    CADCommand,
    NoOpCommand,
    UpdateParametersCommand,
    RegenerateCommand,
    LocateIssueCommand,
    ExplainIssueCommand,
)

logger = logging.getLogger(__name__)
COMMAND_ADAPTER = TypeAdapter(CADCommand)

SYSTEM_PROMPT = """你是一个专业的波峰焊治具工程设计 AI 助手。请以严格的 JSON 格式输出回复，包含 "message" 和 "command" 两个顶层字段。

格式规范：
1. "message": string，面向工程师的中文专业解释或对话回复。
2. "command": object，结构化 CAD 控制指令。

支持的 command 类型：
1. 普通对话/问答/无须修改几何：
   {"message": "您好！我是波峰焊治具 AI 助手，有什么可以帮您？", "command": {"kind": "no_op", "reason": "问候回复", "requiresConfirmation": false}}
2. 调整工程参数（参数名必须以 Mm 结尾，如 sinkClearanceMm, keepoutClearanceMm, solderClearanceMm, filletRadiusMm, clampOffsetMm, railWidthMm, solderBarrierWidthMm, springClipRadiusMm, keepoutInnerFilletMm, solderMinOuterDiameterMm, minimumMaterialWebMm 等）：
   {"message": "已为您将沉板间隙调整为 0.5mm。", "command": {"kind": "update_parameters", "parameters": {"sinkClearanceMm": 0.5}, "reason": "调整沉板间隙", "requiresConfirmation": true}}
3. 重新生成治具：
   {"message": "正在为您重新生成波峰焊治具几何。", "command": {"kind": "regenerate", "reason": "重新生成治具", "requiresConfirmation": true}}
4. 在 CAD 中定位 DRC 问题：
   {"message": "已在图纸中高亮显示该项 DRC 缺陷。", "command": {"kind": "locate_issue", "issueId": "issue-id", "reason": "在图纸中定位", "requiresConfirmation": false}}
5. 解释 DRC 问题：
   {"message": "该避位区因距离元件焊盘过近可能导致锡膏连锡...", "command": {"kind": "explain_issue", "issueId": "issue-id", "reason": "解释 DRC 原因", "requiresConfirmation": false}}

禁止输出非 JSON 格式内容或多余的 Markdown 标记。"""


class AIProviderError(RuntimeError):
    pass


def _extract_json_document(raw: str) -> dict:
    """健壮提取模型返回的 JSON 对象，兼容 Markdown 代码块与部分非结构化输出"""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 尝试提取首个完整的 { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 若模型直接输出了普通文本，包装为合法的 no_op 响应
    return {
        "message": raw[:4000],
        "command": {
            "kind": "no_op",
            "reason": "常规对话回复",
            "requiresConfirmation": False,
        },
    }


def _normalize_command(document: dict, default_message: str) -> tuple[CADCommand, str]:
    """标准化与校验 CADCommand"""
    message = str(document.get("message") or document.get("response") or default_message)[:4000]
    raw_cmd = document.get("command")

    if not isinstance(raw_cmd, dict):
        if isinstance(raw_cmd, str) and raw_cmd in {"no_op", "update_parameters", "regenerate", "locate_issue", "explain_issue"}:
            raw_cmd = {"kind": raw_cmd}
        else:
            raw_cmd = {"kind": "no_op", "reason": message or "常规对话回复", "requiresConfirmation": False}

    kind = raw_cmd.get("kind", "no_op")
    if "reason" not in raw_cmd or not raw_cmd["reason"]:
        raw_cmd["reason"] = message or "常规对话"
    if "requiresConfirmation" not in raw_cmd:
        raw_cmd["requiresConfirmation"] = kind in {"update_parameters", "regenerate"}

    try:
        command = COMMAND_ADAPTER.validate_python(raw_cmd)
    except Exception as exc:
        logger.warning(f"AI 命令验证异常，降级为 no_op: {exc}")
        command = NoOpCommand(kind="no_op", reason=message[:1000] or "常规对话", requiresConfirmation=False)

    return command, message


async def parse_command(message: str, context: dict[str, Any]) -> tuple[CADCommand, str]:
    if not settings.AI_ENABLED or not settings.AI_API_KEY or not settings.AI_MODEL:
        raise AIProviderError("AI 助手尚未配置。请点击右上角齿轮图标配置 API Key 与模型。")
    if len(message) > settings.AI_MAX_INPUT_CHARS:
        raise AIProviderError("AI 指令过长，请缩短后重试。")

    payload = {
        "model": settings.AI_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"message": message, "context": context}, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
    }
    base_url = settings.AI_BASE_URL.rstrip("/")
    url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    
    timeout_sec = min(max(settings.AI_TIMEOUT_MS / 1000, 3.0), 30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}, json=payload)
            
            # 部分第三方端点不支持 response_format="json_object"，如果 400 则降级重试
            if response.status_code == 400 and "response_format" in payload:
                fallback_payload = {**payload}
                fallback_payload.pop("response_format", None)
                response = await client.post(url, headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}, json=fallback_payload)

            # 404 且无 /v1 前缀时，尝试 /v1/chat/completions
            if response.status_code == 404 and not base_url.endswith("/v1"):
                v1_url = f"{base_url}/v1/chat/completions"
                response = await client.post(v1_url, headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}, json=payload)

            if response.status_code == 401:
                raise AIProviderError("AI 服务认证失败，API Key 无效或已过期。")
            elif response.status_code == 429:
                raise AIProviderError("AI 服务调用频次超限或账户余额不足 (429)。")
            elif response.status_code >= 400:
                err_snippet = response.text[:200]
                raise AIProviderError(f"大模型接口返回 HTTP {response.status_code}: {err_snippet}")

            raw = response.json()["choices"][0]["message"]["content"]
            document = _extract_json_document(raw)
            return _normalize_command(document, message)
    except httpx.TimeoutException:
        raise AIProviderError(f"AI 服务请求超时 ({timeout_sec:.0f}s)，请检查 Base URL 是否可访问或增加超时时间。")
    except AIProviderError:
        raise
    except Exception as exc:
        logger.error(f"AI 调用未预期异常: {exc}", exc_info=True)
        raise AIProviderError(f"AI 服务调用异常: {str(exc)}") from exc

