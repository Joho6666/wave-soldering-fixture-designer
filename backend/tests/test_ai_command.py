import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.models.ai_schemas import AICommandRequest, UpdateParametersCommand
from app.services.ai.openai_compatible import AIProviderError, parse_command


def test_ai_request_bounds_and_strict_command_fields():
    request = AICommandRequest(userMessage="把避位间距改成 1.0mm")
    assert request.apply is False
    with pytest.raises(ValidationError):
        UpdateParametersCommand.model_validate({
            "kind": "update_parameters",
            "parameters": {"unknownMm": 1},
            "reason": "bad",
        })


@pytest.mark.asyncio
async def test_unconfigured_provider_fails_closed_without_network():
    old_enabled, old_key, old_model = settings.AI_ENABLED, settings.AI_API_KEY, settings.AI_MODEL
    settings.AI_ENABLED = False
    settings.AI_API_KEY = ""
    settings.AI_MODEL = ""
    try:
        with pytest.raises(AIProviderError, match="尚未配置"):
            await parse_command("解释 DRC", {})
    finally:
        settings.AI_ENABLED, settings.AI_API_KEY, settings.AI_MODEL = old_enabled, old_key, old_model


def test_ai_update_parameters_supports_all_fixture_params():
    cmd = UpdateParametersCommand.model_validate({
        "kind": "update_parameters",
        "parameters": {
            "springClipRadiusMm": 2.5,
            "keepoutInnerFilletMm": 1.2,
            "solderMinOuterDiameterMm": 3.5,
            "minimumMaterialWebMm": 2.5,
            "sinkClearanceMm": 0.3,
        },
        "reason": "优化工艺参数",
    })
    assert cmd.parameters.springClipRadiusMm == 2.5
    assert cmd.parameters.keepoutInnerFilletMm == 1.2
    assert cmd.parameters.solderMinOuterDiameterMm == 3.5
    assert cmd.parameters.minimumMaterialWebMm == 2.5
    vals = cmd.parameters.values()
    assert vals["springClipRadiusMm"] == 2.5