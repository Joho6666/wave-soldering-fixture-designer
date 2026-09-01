from shapely.geometry import box

from app.models.geometry import FixtureGeometry, FixtureRegion, PCBGeometry, DrillHit
from app.services.fixture.drc import run_drc
from app.services.fixture.pressure_relief import generate_pressure_relief


def test_pressure_relief_creates_channel_for_large_pocket():
    body = box(-20, -20, 120, 100)
    pcb = box(0, 0, 40, 30)
    pocket = box(50, 20, 110, 80)
    channels, metas = generate_pressure_relief(
        body=body,
        pcb_outline=pcb,
        keepouts=[pocket],
        keepout_meta=[
            FixtureRegion("k1", "pocket", pocket, "semantic_component", ("U1",), 0.9, parameters={"pocketDepthMm": 2.0})
        ],
        solder_regions=[],
        locating_pins=[],
        clamp_holes=[],
        params={
            "pressureReliefEnabled": True,
            "pressureReliefMinPocketAreaMm2": 100.0,
            "pressureReliefChannelWidthMm": 2.0,
            "pressureReliefEdgeClearanceMm": 3.0,
            "minimumMaterialWebMm": 2.0,
        },
    )
    assert len(channels) >= 1
    assert all(not c.is_empty for c in channels)
    assert metas[0].region_type == "pressure_relief"


def test_pressure_relief_disabled_is_noop():
    channels, metas = generate_pressure_relief(
        body=box(0, 0, 100, 80),
        pcb_outline=box(10, 10, 40, 40),
        keepouts=[box(50, 20, 90, 70)],
        keepout_meta=[],
        solder_regions=[],
        locating_pins=[],
        clamp_holes=[],
        params={"pressureReliefEnabled": False},
    )
    assert channels == []
    assert metas == []


def test_pressure_relief_drc_codes_exist():
    pcb = PCBGeometry(
        outline=box(0, 0, 40, 30),
        holes=[DrillHit("h1", 5, 5, 3.0, False, "T1", "drill"), DrillHit("h2", 35, 25, 3.0, False, "T1", "drill")],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    fixture = FixtureGeometry(
        pcb=pcb,
        body=box(-20, -20, 120, 100),
        sink_region=box(-0.2, -0.2, 40.2, 30.2),
        keepout_regions=[box(50, 20, 110, 80)],
        solder_regions=[],
        locating_pins=[{"id": "p1", "x": 5, "y": 5, "diameter": 2.9}, {"id": "p2", "x": 35, "y": 25, "diameter": 2.9}],
        locating_pin_candidates=[],
        clamp_holes=[{"id": "c1", "x": -10, "y": 40, "diameter": 3.4}, {"id": "c2", "x": 110, "y": 40, "diameter": 3.4}],
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={"minimumMaterialWebMm": 2.0, "palletThicknessMm": 10, "pocketFloorThicknessMm": 2, "solderMinOpeningWidthMm": 1.5, "minPinSeparationMm": 15},
        geometry_sha256="",
        pressure_relief_channels=[box(200, 200, 210, 205)],
    )
    codes = {i["code"] for i in run_drc(fixture)}
    assert "PRESSURE_RELIEF_OUT_OF_FIXTURE" in codes
