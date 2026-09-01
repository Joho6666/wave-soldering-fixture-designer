"""Geometry SHA must change when any production entity changes."""
from shapely.geometry import Polygon, box

from app.models.geometry import FixtureGeometry, FixtureRegion, PCBGeometry
from app.services.fixture.generator import FixtureGenerator


def _pcb():
    return PCBGeometry(
        outline=Polygon([(0, 0), (100, 0), (100, 80), (0, 80)]),
        holes=[],
        layers=[],
        source_sha256="src",
        geometry_sha256="geom",
    )


def _fixture(**overrides):
    pcb = overrides.pop("pcb", None) or _pcb()
    data = dict(
        pcb=pcb,
        body=box(-10, -10, 110, 90),
        sink_region=box(-0.2, -0.2, 100.2, 80.2),
        keepout_regions=[box(10, 10, 20, 20)],
        solder_regions=[box(20, 20, 40, 40)],
        locating_pins=[{"id": "p1", "x": 5.0, "y": 5.0, "diameter": 3.0}],
        locating_pin_candidates=[],
        clamp_holes=[{"id": "c1", "x": 10, "y": 90, "diameter": 3.4}],
        handholds=[box(-9, 20, 1, 60)],
        rails=[box(-10, 85, 110, 90)],
        solder_barriers=[box(-10, 0, 0, 80)],
        solder_barrier_mount_holes=[{"id": "b1", "x": -5, "y": 40, "diameter": 3.2}],
        drc_issues=[],
        review_items=[],
        parameters={"palletThicknessMm": 10.0, "pocketFloorThicknessMm": 2.0, "defaultPocketDepthMm": 2.0, "componentVerticalClearanceMm": 0.5},
        geometry_sha256="",
        spring_clip_holes=[{"id": "s1", "x": 50, "y": 40, "diameter": 4.9}],
        keepout_region_meta=[
            FixtureRegion(
                id="k1",
                region_type="pocket",
                geometry=box(10, 10, 20, 20),
                source_type="semantic_component",
                source_ids=("U1",),
                confidence=0.9,
                parameters={"pocketDepthMm": 2.0, "componentHeightMm": 1.5},
            )
        ],
    )
    data.update(overrides)
    return FixtureGeometry(**data)


def _digest(fixture):
    return FixtureGenerator({"pcb_geometry": fixture.pcb})._geometry_digest(fixture)


def test_geometry_sha_changes_when_handhold_changes():
    base = _digest(_fixture())
    changed = _digest(_fixture(handholds=[box(-9, 20, 2, 61)]))
    assert base != changed
    assert len(base) == 64


def test_geometry_sha_changes_when_rail_changes():
    base = _digest(_fixture())
    changed = _digest(_fixture(rails=[box(-10, 84, 110, 90)]))
    assert base != changed


def test_geometry_sha_changes_when_barrier_changes():
    base = _digest(_fixture())
    changed = _digest(_fixture(solder_barriers=[box(-12, 0, 0, 80)]))
    assert base != changed


def test_geometry_sha_changes_when_pocket_depth_changes():
    base = _digest(_fixture())
    meta = FixtureRegion(
        id="k1",
        region_type="pocket",
        geometry=box(10, 10, 20, 20),
        source_type="semantic_component",
        source_ids=("U1",),
        confidence=0.9,
        parameters={"pocketDepthMm": 3.5, "componentHeightMm": 3.0},
    )
    changed = _digest(_fixture(keepout_region_meta=[meta]))
    assert base != changed


def test_geometry_sha_changes_when_custom_region_changes():
    base = _digest(_fixture())
    changed = _digest(_fixture(keepout_regions=[box(10, 10, 20, 20), box(50, 50, 62, 62)]))
    assert base != changed


def test_geometry_sha_stable_under_reordering():
    f1 = _fixture(
        locating_pins=[{"id": "p1", "x": 5.0, "y": 5.0, "diameter": 3.0}, {"id": "p2", "x": 90.0, "y": 70.0, "diameter": 3.0}],
        keepout_regions=[box(10, 10, 20, 20), box(60, 60, 80, 80)],
    )
    f2 = _fixture(
        locating_pins=[{"id": "p2", "x": 90.0, "y": 70.0, "diameter": 3.0}, {"id": "p1", "x": 5.0, "y": 5.0, "diameter": 3.0}],
        keepout_regions=[box(60, 60, 80, 80), box(10, 10, 20, 20)],
    )
    assert _digest(f1) == _digest(f2)
