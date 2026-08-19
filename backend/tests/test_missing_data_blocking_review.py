"""Tests for missing data generating mandatory blocking reviews."""
import pytest
from shapely.geometry import Polygon

from app.models.geometry import PCBGeometry, DrillHit
from app.services.fixture.generator import FixtureGenerator


def _make_pcb(
    bot_silk=None,
    bot_mask=None,
    top_silk=None,
    holes=None,
):
    outline = Polygon([(0, 0), (100, 0), (100, 80), (0, 80)])
    if holes is None:
        holes = [
            DrillHit("d1", 5.0, 5.0, 3.0, False, "T1", "layer-drill"),
            DrillHit("d2", 95.0, 75.0, 3.0, False, "T1", "layer-drill"),
        ]
    return PCBGeometry(
        outline=outline,
        holes=holes,
        layers=[],
        source_sha256="test",
        geometry_sha256="test",
        bottom_silkscreen=bot_silk,
        bottom_soldermask=bot_mask,
        top_silkscreen=top_silk,
    )


class TestMissingDataBlockingReview:
    def test_missing_gbo_gbs_creates_mandatory_review(self):
        pcb = _make_pcb(bot_silk=None, bot_mask=None)
        gen = FixtureGenerator({"pcb_geometry": pcb})
        result = gen.generate({})
        reviews = result["reviewItems"]
        bot_reviews = [r for r in reviews if r["type"] == "CONFIRM_NO_BOTTOM_SMD"]
        assert len(bot_reviews) == 1
        assert bot_reviews[0]["mandatory"] is True
        assert bot_reviews[0]["status"] == "pending"

    def test_missing_gto_creates_mandatory_review(self):
        pcb = _make_pcb(top_silk=None)
        gen = FixtureGenerator({"pcb_geometry": pcb})
        result = gen.generate({})
        reviews = result["reviewItems"]
        gto_reviews = [r for r in reviews if r["type"] == "CONFIRM_NO_SPRING_CLIP_REQUIRED"]
        assert len(gto_reviews) == 1
        assert gto_reviews[0]["mandatory"] is True

    def test_no_pth_creates_mandatory_review(self):
        npth_holes = [
            DrillHit("d1", 5.0, 5.0, 3.0, False, "T1", "layer-drill"),
            DrillHit("d2", 95.0, 75.0, 3.0, False, "T1", "layer-drill"),
        ]
        pcb = _make_pcb(holes=npth_holes)
        gen = FixtureGenerator({"pcb_geometry": pcb})
        result = gen.generate({})
        reviews = result["reviewItems"]
        tht_reviews = [r for r in reviews if r["type"] == "CONFIRM_NO_TOP_THT"]
        assert len(tht_reviews) == 1
        assert tht_reviews[0]["mandatory"] is True

    def test_no_holes_creates_npth_mandatory_review(self):
        pcb = _make_pcb(holes=[])
        gen = FixtureGenerator({"pcb_geometry": pcb})
        result = gen.generate({})
        reviews = result["reviewItems"]
        npth_reviews = [r for r in reviews if r["type"] == "CONFIRM_NO_NPTH_AVAILABLE"]
        assert len(npth_reviews) == 1
        assert npth_reviews[0]["mandatory"] is True

    def test_accepted_confirm_no_bottom_smd_allows_generation(self):
        pcb = _make_pcb(bot_silk=None, bot_mask=None)
        gen = FixtureGenerator({"pcb_geometry": pcb})
        result = gen.generate(
            {},
            review_actions={"review-bot-keepout-missing-layer": "accepted"},
        )
        reviews = result["reviewItems"]
        bot_reviews = [r for r in reviews if r["type"] == "CONFIRM_NO_BOTTOM_SMD"]
        assert len(bot_reviews) == 1
        assert bot_reviews[0]["status"] == "accepted"
