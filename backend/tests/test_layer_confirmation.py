from pathlib import Path
import pytest
from app.services.gerber.parser import GerberParser

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_layer_confirmation_flow():
    # 模拟用户人工指定层映射
    confirmed_layers = [
        {"filename": "01_espmh_board_outline.GBR", "type": "board_outline"},
        {"filename": "03_espmh_drill.DRL", "type": "drill"},
    ]
    parser = GerberParser()
    result = parser.parse_zip(str(FIXTURE_ARCHIVE), confirmed_layers=confirmed_layers)
    
    assert result["outlineClosed"] is True
    assert result["width"] == 25.654
    assert result["holeCount"] == 31
