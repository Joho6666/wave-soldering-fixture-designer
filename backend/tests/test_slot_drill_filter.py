import pytest
from shapely.geometry import Polygon
from app.models.geometry import PCBGeometry, DrillHit
from app.services.fixture.generator import FixtureGenerator


def test_slot_drills_are_excluded_from_locating_pins():
    outline = Polygon([(0, 0), (100, 0), (100, 80), (0, 80)])
    holes = [
        # 圆孔 NPTH
        DrillHit(id="h1", x=5.0, y=5.0, diameter_mm=3.0, plated=False, tool_id="T1", source_layer_id="drl", kind="hole"),
        DrillHit(id="h2", x=95.0, y=75.0, diameter_mm=3.0, plated=False, tool_id="T1", source_layer_id="drl", kind="hole"),
        # 铣槽 slot
        DrillHit(id="slot1", x=5.0, y=75.0, diameter_mm=3.0, plated=False, tool_id="T2", source_layer_id="drl", kind="slot"),
    ]
    pcb = PCBGeometry(
        outline=outline,
        holes=holes,
        layers=[],
        source_sha256="src",
        geometry_sha256="geom",
    )
    gen = FixtureGenerator({"pcb_geometry": pcb})
    cands, pins, _ = gen._locating_pin_candidates({})

    slot_cand = next(c for c in cands if c["drillId"] == "slot1")
    assert slot_cand["eligible"] is False
    assert any("腰圆槽" in r for r in slot_cand["rejectionReasons"])

    selected_ids = {p["id"] for p in pins}
    assert "pin-slot1" not in selected_ids
    assert "pin-h1" in selected_ids
    assert "pin-h2" in selected_ids
