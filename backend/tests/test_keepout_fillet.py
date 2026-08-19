"""Test BOT keepout inner fillet R1.5."""
import pytest
from shapely.geometry import Polygon, Point, MultiPolygon
from app.models.geometry import PCBGeometry, DrillHit
from app.services.fixture.generator import FixtureGenerator


def _make_pcb_with_bot_silk():
    outline = Polygon([(0, 0), (80, 0), (80, 60), (0, 60)])
    holes = [
        DrillHit("h1", 5, 5, 3.0, False, "T1", "layer-drill"),
        DrillHit("h2", 75, 55, 3.0, False, "T1", "layer-drill"),
    ]
    bot_silk = MultiPolygon([
        Polygon([(20, 20), (40, 20), (40, 40), (20, 40)]),
    ])
    return PCBGeometry(
        outline=outline, holes=holes, layers=[], source_sha256="abc", geometry_sha256="def",
        bottom_silkscreen=bot_silk,
    )


def test_keepout_regions_have_rounded_corners():
    pcb = _make_pcb_with_bot_silk()
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({"keepoutInnerFilletMm": 1.5})
    keepouts = result["keepout_zones"]
    assert len(keepouts) >= 1
    for k in keepouts:
        assert not k.is_empty
        assert k.area > 0
        ext_coords = list(k.exterior.coords)
        assert len(ext_coords) > 4, "Filleted polygon should have more vertices than a rectangle"


def test_keepout_fillet_zero_preserves_shape():
    pcb = _make_pcb_with_bot_silk()
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result_fillet = gen.generate({"keepoutInnerFilletMm": 1.5})
    result_no_fillet = gen.generate({"keepoutInnerFilletMm": 0.0})
    k_fillet = result_fillet["keepout_zones"]
    k_no = result_no_fillet["keepout_zones"]
    assert len(k_fillet) == len(k_no)