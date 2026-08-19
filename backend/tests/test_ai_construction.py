import pytest
from app.models.ai_schemas import (
    ApplyRecipePresetCommand,
    SetLocatingPinsCommand,
    AddCustomRegionCommand,
    AutoFixDrcCommand,
    ParameterPatch,
)
from app.services.ai.openai_compatible import _normalize_command, RECIPE_PRESETS, COMMAND_ADAPTER

def test_apply_recipe_preset_schema():
    raw = {
        "kind": "apply_recipe_preset",
        "presetId": "automotive_high_reliability",
        "parameters": {"keepoutClearanceMm": 1.0, "minimumMaterialWebMm": 2.5},
        "reason": "汽车电子高可靠性标准",
    }
    cmd = COMMAND_ADAPTER.validate_python(raw)
    assert isinstance(cmd, ApplyRecipePresetCommand)
    assert cmd.presetId == "automotive_high_reliability"
    assert cmd.parameters.keepoutClearanceMm == 1.0
    assert cmd.requiresConfirmation is True

def test_set_locating_pins_schema():
    raw = {
        "kind": "set_locating_pins",
        "pinDrillIds": ["D1", "D2"],
        "reason": "选用对角定位孔",
    }
    cmd = COMMAND_ADAPTER.validate_python(raw)
    assert isinstance(cmd, SetLocatingPinsCommand)
    assert cmd.pinDrillIds == ["D1", "D2"]
    assert cmd.requiresConfirmation is True

def test_add_custom_region_schema():
    raw = {
        "kind": "add_custom_region",
        "regionType": "keepout",
        "x": 50.0,
        "y": 30.0,
        "width": 20.0,
        "height": 10.0,
        "label": "J1排针避位",
        "reason": "非标避位开槽",
    }
    cmd = COMMAND_ADAPTER.validate_python(raw)
    assert isinstance(cmd, AddCustomRegionCommand)
    assert cmd.regionType == "keepout"
    assert cmd.x == 50.0
    assert cmd.width == 20.0
    assert cmd.requiresConfirmation is True

def test_auto_fix_drc_schema():
    raw = {
        "kind": "auto_fix_drc",
        "targetIssueIds": ["drc-minimum_material_web_too_small-global"],
        "suggestedParameters": {"solderClearanceMm": 2.5},
        "reason": "消除壁厚不足",
    }
    cmd = COMMAND_ADAPTER.validate_python(raw)
    assert isinstance(cmd, AutoFixDrcCommand)
    assert cmd.suggestedParameters.solderClearanceMm == 2.5
    assert cmd.requiresConfirmation is True

def test_recipe_preset_auto_fill():
    doc = {
        "message": "已为您应用汽车电子标准",
        "command": {
            "kind": "apply_recipe_preset",
            "presetId": "automotive_high_reliability",
        },
    }
    cmd, msg = _normalize_command(doc, "默认消息")
    assert isinstance(cmd, ApplyRecipePresetCommand)
    assert cmd.presetName == RECIPE_PRESETS["automotive_high_reliability"]["name"]
    assert cmd.parameters.keepoutClearanceMm == 1.0
