from pathlib import Path
import pytest
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"
PARAMETERS = {
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

def test_review_accept_unlocks_status():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    generator = FixtureGenerator(analysis)
    
    # 第一次生成：存在 pending review 项
    gen1 = generator.generate(PARAMETERS)
    assert gen1["status"] == "review_required"
    
    # 模拟用户指定定位销并确认全部待审核项
    actions = {item["id"]: "accepted" for item in gen1["reviewItems"]}
    drill_ids = [analysis["holes"][0]["id"], analysis["holes"][1]["id"]]
    gen2 = generator.generate(PARAMETERS, review_actions=actions, manual_pins=drill_ids)
    
    assert gen2["status"] == "completed"
    assert gen2["featureSummary"]["locatingPinCount"] >= 1


def test_reject_solder_review_excludes_region():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    generator = FixtureGenerator(analysis)
    
    gen_all = generator.generate(PARAMETERS)
    initial_solder_count = gen_all["featureSummary"]["solderWindowCount"]
    
    # 查找是否有 top_solder_region 审核项
    solder_reviews = [r for r in gen_all["reviewItems"] if r["type"] == "top_solder_region"]
    if solder_reviews:
        target_rev = solder_reviews[0]
        actions = {target_rev["id"]: "rejected"}
        gen_rejected = generator.generate(PARAMETERS, review_actions=actions)
        assert gen_rejected["featureSummary"]["solderWindowCount"] == initial_solder_count - 1


def test_manual_pins_preserved_when_specified():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    generator = FixtureGenerator(analysis)
    
    holes = analysis["holes"]
    assert len(holes) >= 2
    selected_drills = [holes[0]["id"], holes[1]["id"]]
    
    gen = generator.generate(PARAMETERS, manual_pins=selected_drills)
    assert gen["featureSummary"]["locatingPinCount"] == 2
    pin_ids = [c["drillId"] for c in gen["locating_candidates"] if c["selected"]]
    assert set(pin_ids) == set(selected_drills)