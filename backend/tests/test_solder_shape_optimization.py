"""Test TOP solder window shape optimization."""
import pytest
from shapely.geometry import Polygon, Point
from app.models.geometry import PCBGeometry, DrillHit
from app.services.fixture.generator import FixtureGenerator


def _make_pcb_with_mask():
    outline = Polygon([(0, 0), (80, 0), (80, 60), (0, 60)])
    holes = [
        DrillHit("pth1", 30, 30, 1.0, True, "T1", "layer-drill"),
        DrillHit("pth2", 33, 30, 1.0, True, "T1", "layer-drill"),
        DrillHit("pth3", 36, 30, 1.0, True, "T1", "layer-drill"),
    ]
    bot_mask = Polygon([(25, 25), (42, 25), (42, 35), (25, 35)])
    return PCBGeometry(
        outline=outline, holes=holes, layers=[], source_sha256="abc", geometry_sha256="def",
        bottom_soldermask=bot_mask,
    )


def test_solder_regions_not_degenerate():
    pcb = _make_pcb_with_mask()
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({})
    windows = result["solder_windows"]
    assert len(windows) >= 1
    for w in windows:
        assert w.area > 0.5, "Solder window should not degenerate to a point"


def test_solder_min_outer_diameter():
    pcb = _make_pcb_with_mask()
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({"solderMinOuterDiameterMm": 3.0})
    windows = result["solder_windows"]
    assert len(windows) >= 1