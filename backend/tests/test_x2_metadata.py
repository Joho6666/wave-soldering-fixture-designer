from pathlib import Path
import pytest
from app.services.gerber.parser import GerberParser

def test_x2_metadata_nonstandard_names():
    """Verify that nonstandard filenames with X2 metadata (%TF.FileFunction) are identified correctly."""
    case_004 = Path(__file__).parent / "fixtures" / "CASE-004_x2_nonstandard_names.zip"
    assert case_004.exists(), f"Missing fixture {case_004}"

    res = GerberParser().parse_zip(str(case_004))
    layer_map = {layer["filename"]: layer["type"] for layer in res["layers"]}
    confidence_map = {layer["filename"]: layer["confidence"] for layer in res["layers"]}

    assert layer_map.get("001.gbr") == "board_outline"
    assert confidence_map.get("001.gbr") >= 0.95

    assert layer_map.get("002.gbr") == "bottom_silkscreen"
    assert confidence_map.get("002.gbr") >= 0.95

    assert layer_map.get("003.gbr") == "top_silkscreen"
    assert confidence_map.get("003.gbr") >= 0.95

    assert layer_map.get("004.gbr") == "bottom_soldermask"
    assert confidence_map.get("004.gbr") >= 0.95

    assert res["outlineClosed"] is True
    assert res.get("requires_layer_confirmation") is not True
