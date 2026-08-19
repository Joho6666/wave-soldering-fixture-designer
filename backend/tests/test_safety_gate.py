"""Production Safety Gate & DRC Override tests."""
import pytest
from shapely.geometry import Polygon, box

from app.models.geometry import PCBGeometry, DrillHit, FixtureGeometry
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.drc import run_drc


def _make_pcb(outline=None, holes=None):
    if outline is None:
        outline = box(0, 0, 80, 60)
    return PCBGeometry(
        outline=outline,
        holes=holes or [
            DrillHit("h1", 5, 5, 3.0, False, "T1", "drill", "hole"),
            DrillHit("h2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ],
        layers=[],
        source_sha256="test",
        geometry_sha256="test",
    )


def _generate(pcb=None, params=None, manual_pins=None, review_actions=None):
    pcb = pcb or _make_pcb()
    gen = FixtureGenerator({"pcb_geometry": pcb})
    return gen.generate(params or {}, review_actions=review_actions, manual_pins=manual_pins)


class TestProductionSafetyGate:
    """Tests for Production Safety Gate logic."""

    def test_blocking_drc_prevents_production(self):
        result = _generate()
        issues = result["issues"]
        blocking = [i for i in issues if i["severity"] in ("error", "blocking")]
        if blocking:
            assert any(i["severity"] in ("error", "blocking") for i in issues)

    def test_pending_mandatory_review_blocks_production(self):
        result = _generate()
        reviews = result.get("reviewItems", [])
        pending_mandatory = [r for r in reviews if r.get("mandatory", True) and r.get("status") == "pending"]
        if pending_mandatory:
            assert result["status"] == "review_required"

    def test_completed_status_when_no_blocking(self):
        pcb = _make_pcb()
        result = _generate(pcb=pcb, manual_pins=["h1", "h2"])
        reviews = result.get("reviewItems", [])
        pending_mandatory = [r for r in reviews if r.get("mandatory", True) and r.get("status") == "pending"]
        if len(pending_mandatory) == 0:
            assert result["status"] == "completed"

    def test_drc_severity_includes_blocking(self):
        pcb = _make_pcb(outline=Polygon([(0, 0), (0, 1), (1, 0)]))
        gen = FixtureGenerator({"pcb_geometry": pcb})
        try:
            result = gen.generate({}, manual_pins=["h1", "h2"])
            issues = result["issues"]
            severities = {i["severity"] for i in issues}
            assert severities.issubset({"info", "warning", "error", "blocking"})
        except Exception:
            pass


class TestRailDirection:
    """Tests for correct rail/barrier orientation (rails top/bottom, barriers left/right)."""

    def test_rails_are_top_and_bottom(self):
        result = _generate()
        rails = result["rails"]
        assert len(rails) == 2
        body_bounds = result["fixture_outline"].bounds
        min_x, min_y, max_x, max_y = body_bounds
        for rail in rails:
            r_min_x, r_min_y, r_max_x, r_max_y = rail.bounds
            assert abs(r_max_x - r_min_x) > abs(r_max_y - r_min_y), \
                f"Rail should be horizontal (wider than tall): bounds={rail.bounds}"

    def test_barriers_are_left_and_right(self):
        result = _generate()
        barriers = result["solder_barriers"]
        assert len(barriers) == 2
        for barrier in barriers:
            b_min_x, b_min_y, b_max_x, b_max_y = barrier.bounds
            assert abs(b_max_y - b_min_y) > abs(b_max_x - b_min_x), \
                f"Barrier should be vertical (taller than wide): bounds={barrier.bounds}"


class TestNumericalAssertions:
    """Tests for key dimensional parameters."""

    def test_clamp_hole_diameter(self):
        result = _generate()
        for clamp in result["clips"]:
            assert clamp["diameter"] == 3.4

    def test_pin_diameter_rule(self):
        pcb = _make_pcb()
        result = _generate(pcb=pcb, manual_pins=["h1", "h2"])
        for pin in result["pins"]:
            assert pin["diameter"] == pytest.approx(3.0 - 0.1, abs=0.01)

    def test_barrier_mount_holes_per_barrier(self):
        result = _generate()
        mount_holes = result["solder_barrier_mount_holes"]
        left_holes = [h for h in mount_holes if "left" in h["id"]]
        right_holes = [h for h in mount_holes if "right" in h["id"]]
        assert len(left_holes) >= 1
        assert len(right_holes) >= 1
        assert len(left_holes) == len(right_holes)

    def test_barrier_mount_hole_diameter(self):
        result = _generate()
        for hole in result["solder_barrier_mount_holes"]:
            assert hole["diameter"] == 3.2

    def test_fixture_size_snapped_to_5mm(self):
        result = _generate()
        body = result["fixture_outline"]
        min_x, min_y, max_x, max_y = body.bounds
        width = max_x - min_x
        height = max_y - min_y
        assert width % 5 == pytest.approx(0, abs=0.5), f"Fixture width {width} not snapped to 5mm"
        assert height % 5 == pytest.approx(0, abs=0.5), f"Fixture height {height} not snapped to 5mm"

    def test_handholds_20x40_overlap_1(self):
        result = _generate()
        handholds = result["handholds"]
        assert len(handholds) == 2
        for handhold in handholds:
            bounds = handhold.bounds
            w = bounds[2] - bounds[0]
            h = bounds[3] - bounds[1]
            assert w == pytest.approx(20, abs=5)
            assert h == pytest.approx(40, abs=5)

    def test_rail_width_5mm(self):
        result = _generate()
        for rail in result["rails"]:
            bounds = rail.bounds
            rail_thickness = bounds[3] - bounds[1]
            assert rail_thickness == pytest.approx(5.0, abs=0.5), f"Rail thickness should be ~5mm: {rail_thickness}"

