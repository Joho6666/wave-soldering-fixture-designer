import json
from pathlib import Path
import pytest
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "production_samples" / "case_001_standard_demo"

def test_production_sample_case_001():
    zip_path = SAMPLE_DIR / "wave_fixture_outline_drill.zip"
    expected_path = SAMPLE_DIR / "expected.json"
    
    assert zip_path.exists(), f"Sample zip missing: {zip_path}"
    assert expected_path.exists(), f"Expected json missing: {expected_path}"
    
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    analysis = GerberParser().parse_zip(str(zip_path))
    assert abs(analysis["width"] - expected["boardWidthMm"]) < 0.1
    assert abs(analysis["height"] - expected["boardHeightMm"]) < 0.1
    assert analysis["holeCount"] == expected["holeCount"]
    
    generator = FixtureGenerator(analysis)
    params = {
        "sinkClearanceMm": 0.2,
        "keepoutClearanceMm": 0.7,
        "solderClearanceMm": 3.0,
        "filletRadiusMm": 1.85,
        "clampHoleDiameterMm": 3.4,
        "clampOffsetMm": 10,
        "handholdWidthMm": 20,
        "handholdHeightMm": 40,
        "handholdOverlapMm": 1,
        "handholdCornerRadiusMm": 2,
        "fixtureMarginXmm": 20,
        "fixtureMarginYmm": 30,
        "fixtureCornerRadiusMm": 5,
        "railWidthMm": 5,
        "solderBarrierWidthMm": 10,
    }
    fixture = generator.generate(params)
    assert abs(fixture["fixtureWidth"] - expected["fixtureWidthMm"]) < 0.5
    assert abs(fixture["fixtureHeight"] - expected["fixtureHeightMm"]) < 0.5
    assert fixture["featureSummary"]["solderWindowCount"] == expected["solderRegionCount"]
