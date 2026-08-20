import pytest
from shapely.geometry import Polygon, box
from app.models.geometry import FixtureGeometry, PCBGeometry, DrillHit
from app.services.fixture.drc import run_drc
from app.services.fixture.generator import FixtureGenerator


def _make_fixture_with_clamps(clamp_holes):
    pcb = PCBGeometry(
        outline=Polygon([(0, 0), (100, 0), (100, 80), (0, 80)]),
        holes=[],
        layers=[],
        source_sha256="src",
        geometry_sha256="geom",
    )
    return FixtureGeometry(
        pcb=pcb,
        body=box(-10, -10, 110, 90),
        sink_region=box(-0.2, -0.2, 100.2, 80.2),
        keepout_regions=[],
        solder_regions=[],
        locating_pins=[{"id": "p1", "x": 5, "y": 5, "diameter": 3.0}, {"id": "p2", "x": 95, "y": 75, "diameter": 3.0}],
        locating_pin_candidates=[],
        clamp_holes=clamp_holes,
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={"minimumMaterialWebMm": 2.0},
        geometry_sha256="",
        spring_clip_holes=[],
    )


def test_clamp_outside_fixture_body_triggers_drc_error():
    # 压扣孔 (50, 120) 位于 body (y<=90) 外部
    clamps = [
        {"id": "clamp-1", "x": 50.0, "y": 120.0, "diameter": 3.4},
        {"id": "clamp-2", "x": 50.0, "y": -5.0, "diameter": 3.4},
    ]
    f = _make_fixture_with_clamps(clamps)
    issues = run_drc(f)
    overflow_issues = [i for i in issues if i["code"] == "CLAMP_FIXTURE_COLLISION"]
    assert len(overflow_issues) >= 1
    assert overflow_issues[0]["severity"] == "error"


def test_clamp_inside_sink_region_triggers_drc_error():
    # 压扣孔 (50, 40) 落在沉板区内部
    clamps = [
        {"id": "clamp-1", "x": 50.0, "y": 40.0, "diameter": 3.4},
        {"id": "clamp-2", "x": 50.0, "y": -5.0, "diameter": 3.4},
    ]
    f = _make_fixture_with_clamps(clamps)
    issues = run_drc(f)
    sink_collision_issues = [i for i in issues if i["code"] == "CLAMP_SINK_COLLISION"]
    assert len(sink_collision_issues) >= 1
    assert sink_collision_issues[0]["severity"] == "error"


def test_handholds_with_large_corner_radius():
    pcb = PCBGeometry(
        outline=Polygon([(0, 0), (100, 0), (100, 80), (0, 80)]),
        holes=[],
        layers=[],
        source_sha256="src",
        geometry_sha256="geom",
    )
    gen = FixtureGenerator({"pcb_geometry": pcb})
    # 传入超大圆角 radius = 50.0
    params = gen._parameters({"handholdCornerRadiusMm": 50.0})
    sink = box(-0.2, -0.2, 100.2, 80.2)
    hhs = gen._handholds(sink, params)
    assert len(hhs) == 2
    assert all(not h.is_empty and h.is_valid and h.area > 0 for h in hhs)
