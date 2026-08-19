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
    ApplyRecipePresetCommand,
    SetLocatingPinsCommand,
    AddCustomRegionCommand,
    AutoFixDrcCommand,
    RegenerateCommand,
    LocateIssueCommand,
    ExplainIssueCommand,
)

logger = logging.getLogger(__name__)
COMMAND_ADAPTER = TypeAdapter(CADCommand)

RECIPE_PRESETS = {
    "automotive_high_reliability": {
        "name": "汽车电子高可靠性标准",
        "description": "加宽避位安全裕量至 1.0mm，壁厚 >= 2.5mm，加大压扣偏移防振",
        "parameters": {
            "sinkClearanceMm": 0.3,
            "keepoutClearanceMm": 1.0,
            "solderClearanceMm": 3.5,
            "clampOffsetMm": 12.0,
            "minimumMaterialWebMm": 2.5,
            "solderMinOuterDiameterMm": 3.2,
            "keepoutInnerFilletMm": 1.5,
            "fixtureMarginXmm": 25.0,
            "fixtureMarginYmm": 35.0,
        },
    },
    "dense_consumer": {
        "name": "高密消费电子微间距标准",
        "description": "紧凑微间距避位 0.5mm，上锡开窗 2.0mm，紧凑边距以适应狭小拼板",
        "parameters": {
            "sinkClearanceMm": 0.15,
            "keepoutClearanceMm": 0.5,
            "solderClearanceMm": 2.0,
            "minimumMaterialWebMm": 1.5,
            "solderMinOuterDiameterMm": 2.5,
            "keepoutInnerFilletMm": 1.0,
            "fixtureMarginXmm": 18.0,
            "fixtureMarginYmm": 25.0,
        },
    },
    "thick_copper_heavy": {
        "name": "厚铜重载治具标准",
        "description": "强化治具外框边距 (30×40mm)，加宽取手位与导轨，提升耐热形变刚度",
        "parameters": {
            "sinkClearanceMm": 0.25,
            "keepoutClearanceMm": 0.8,
            "solderClearanceMm": 3.5,
            "minimumMaterialWebMm": 2.5,
            "fixtureMarginXmm": 30.0,
            "fixtureMarginYmm": 40.0,
            "handholdWidthMm": 25.0,
            "handholdHeightMm": 50.0,
            "railWidthMm": 6.0,
            "solderBarrierWidthMm": 12.0,
        },
    },
    "standard": {
        "name": "标准波峰焊通用规范",
        "description": "标准沉板 0.2mm，避位 0.7mm，上锡 3.0mm，壁厚 2.0mm",
        "parameters": {
            "sinkClearanceMm": 0.2,
            "keepoutClearanceMm": 0.7,
            "solderClearanceMm": 3.0,
            "filletRadiusMm": 1.85,
            "clampHoleDiameterMm": 3.4,
            "clampOffsetMm": 10.0,
            "handholdWidthMm": 20.0,
            "handholdHeightMm": 40.0,
            "handholdOverlapMm": 1.0,
            "handholdCornerRadiusMm": 2.0,
            "fixtureMarginXmm": 20.0,
            "fixtureMarginYmm": 30.0,
            "fixtureCornerRadiusMm": 5.0,
            "railWidthMm": 5.0,
            "solderBarrierWidthMm": 10.0,
            "minimumMaterialWebMm": 2.0,
            "springClipRadiusMm": 2.45,
            "keepoutInnerFilletMm": 1.5,
            "solderMinOuterDiameterMm": 3.0,
            "fixtureSizeRoundStepMm": 5.0,
        },
    },
}

SYSTEM_PROMPT = """你是一个专业的波峰焊治具工程设计 AI 助手。你能够深度参与治具的建设、优化与审查。
请以严格的 JSON 格式输出回复，包含 "message" 和 "command" 两个顶层字段。

格式规范：
1. "message": string，面向工程师的中文专业解释、设计建议或分析说明。
2. "command": object，结构化 CAD 建设/控制指令。

支持的 command 类型：
1. 【工艺配方建设】应用标准化配方预设（automotive_high_reliability / dense_consumer / thick_copper_heavy / standard）：
   {"message": "已为您推荐并配置汽车电子高可靠性工艺配方...", "command": {"kind": "apply_recipe_preset", "presetId": "automotive_high_reliability", "presetName": "汽车电子高可靠性标准", "parameters": {"keepoutClearanceMm": 1.0, "minimumMaterialWebMm": 2.5, "solderClearanceMm": 3.5}, "reason": "提升耐温抗振裕量", "requiresConfirmation": true}}

2. 【定位孔方案建设】指定/切换定位销方案（从 context 中的 locatingCandidates 筛选合适钻孔 drillId）：
   {"message": "已为您优选对角两处 Ø3.2mm NPTH 机械定位孔...", "command": {"kind": "set_locating_pins", "pinDrillIds": ["D1", "D2"], "reason": "选用对角非金属化定位孔", "requiresConfirmation": true}}

3. 【自定义几何开窗建设】在指定坐标新增非标避位槽或透锡槽（keepout / solder）：
   {"message": "已在指定坐标 (50, 30) 处规划 20×15mm 自定义避位槽...", "command": {"kind": "add_custom_region", "regionType": "keepout", "x": 50.0, "y": 30.0, "width": 20.0, "height": 15.0, "label": "J1排针避位", "reason": "避让非标接插件", "requiresConfirmation": true}}

4. 【DRC 缺陷自动修复建设】针对壁厚不足、干涉等 DRC 错误，自动计算修复参数方案：
   {"message": "检测到上锡窗口与沉板边材料壁厚过薄，建议将 solderClearanceMm 微调至 2.5mm 以满足 2.0mm 最小壁厚要求。", "command": {"kind": "auto_fix_drc", "targetIssueIds": ["drc-minimum_material_web_too_small-global"], "suggestedParameters": {"solderClearanceMm": 2.5}, "reason": "消除壁厚过薄 DRC 违规", "requiresConfirmation": true}}

5. 【单项参数微调】
   {"message": "已将避位安全距离调整为 1.2mm。", "command": {"kind": "update_parameters", "parameters": {"keepoutClearanceMm": 1.2}, "reason": "调整避位间距", "requiresConfirmation": true}}

6. 【重新生成出图】
   {"message": "正在为您重新计算治具几何。", "command": {"kind": "regenerate", "reason": "重新生成治具", "requiresConfirmation": true}}

7. 【定位与解释缺陷】
   {"message": "已在图纸中定位并高亮该项缺陷。", "command": {"kind": "locate_issue", "issueId": "drc-xxx", "reason": "定位缺陷", "requiresConfirmation": false}}
   {"message": "该避位区由于周边贴片电容密集，建议扩孔...", "command": {"kind": "explain_issue", "issueId": "drc-xxx", "reason": "解释缺陷原因", "requiresConfirmation": false}}

8. 【普通对话与咨询】
   {"message": "您好！我是波峰焊治具 AI 助手，有什么可以帮您？", "command": {"kind": "no_op", "reason": "问候回复", "requiresConfirmation": false}}

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

    valid_kinds = {
        "no_op",
        "update_parameters",
        "apply_recipe_preset",
        "set_locating_pins",
        "add_custom_region",
        "auto_fix_drc",
        "regenerate",
        "locate_issue",
        "explain_issue",
    }

    if not isinstance(raw_cmd, dict):
        if isinstance(raw_cmd, str) and raw_cmd in valid_kinds:
            raw_cmd = {"kind": raw_cmd}
        else:
            raw_cmd = {"kind": "no_op", "reason": message or "常规对话回复", "requiresConfirmation": False}

    kind = raw_cmd.get("kind", "no_op")
    if "reason" not in raw_cmd or not raw_cmd["reason"]:
        raw_cmd["reason"] = message or "常规对话"
    if "requiresConfirmation" not in raw_cmd:
        raw_cmd["requiresConfirmation"] = kind in {
            "update_parameters",
            "apply_recipe_preset",
            "set_locating_pins",
            "add_custom_region",
            "auto_fix_drc",
            "regenerate",
        }

    # 如果是 apply_recipe_preset 且缺参数，自动从内置预设补全
    if kind == "apply_recipe_preset":
        pid = raw_cmd.get("presetId", "standard")
        if pid in RECIPE_PRESETS:
            preset = RECIPE_PRESETS[pid]
            if not raw_cmd.get("presetName"):
                raw_cmd["presetName"] = preset["name"]
            if not raw_cmd.get("parameters"):
                raw_cmd["parameters"] = preset["parameters"]

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
