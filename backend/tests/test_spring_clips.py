"""Test spring clip hole generation from TOP silkscreen (GTO)."""
import pytest
from shapely.geometry import Polygon, Point, MultiPolygon
from app.models.geometry import PCBGeometry, DrillHit
from app.services.fixture.generator import FixtureGenerator


def _make_pcb(top_silk=None):
    outline = Polygon([(0, 0), (80, 0), (80, 60), (0, 60)])
    holes = [
        DrillHit("h1", 5, 5, 3.0, False, "T1", "layer-drill"),
        DrillHit("h2", 75, 55, 3.0, False, "T1", "layer-drill"),
    ]
    return PCBGeometry(
        outline=outline, holes=holes, layers=[], source_sha256="abc", geometry_sha256="def",
        top_silkscreen=top_silk,
    )


def test_spring_clips_generated_from_silkscreen():
    silk_region = MultiPolygon([
        Point(20, 30).buffer(5),
        Point(60, 30).buffer(5),
    ])
    pcb = _make_pcb(top_silk=silk_region)
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({})
    clips = result["spring_clips"]
    assert len(clips) >= 2
    assert all(c["diameter"] == pytest.approx(4.9, abs=0.1) for c in clips)


def test_spring_clips_missing_gto_generates_review():
    pcb = _make_pcb(top_silk=None)
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({})
    clips = result["spring_clips"]
    assert len(clips) == 0
    reviews = [r for r in result["reviewItems"] if r["type"] in ("front_panel_clip", "CONFIRM_NO_SPRING_CLIP_REQUIRED")]
    assert len(reviews) >= 1


def test_spring_clip_in_feature_summary():
    pcb = _make_pcb(top_silk=Point(40, 30).buffer(5))
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({})
    assert "springClipCount" in result["featureSummary"]