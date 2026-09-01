"""Regressions for remaining P0/P1 correctness bugs."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from shapely.geometry import box

from app.api.v1.jobs import _compute_production_gate, complete_all_reviews
from app.geometry.digest import geometry_digest
from app.geometry.transform import Transform2D
from app.models.geometry import DrillHit, FixtureGeometry, FixtureRegion, PCBGeometry
from app.models.job import Job
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.pressure_relief import generate_pressure_relief
from validation.golden_validator import overlay_svg
from validation.lifecycle import can_advance
from validation.manual_dxf_parser import ManualFixtureData


def test_rejected_mandatory_review_blocks_complete_and_gate():
    reviews = [
        {"id": "r1", "type": "CONFIRM_NO_NPTH_AVAILABLE", "status": "rejected", "mandatory": True,
         "title": "test", "description": "test", "confidence": 0.4},
    ]
    job = MagicMock(spec=Job)
    job.id = "job-rej"
    job.status = "completed"
    job.result_data = {"reviewItems": reviews, "issues": [], "drcOverrides": [], "geometrySha256": "abc"}
    job.logs = []
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = job
    with pytest.raises(HTTPException) as exc:
        asyncio.get_event_loop().run_until_complete(complete_all_reviews("job-rej", db))
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "REJECTED_MANDATORY_REVIEWS"

    gate = _compute_production_gate(job)
    assert gate.production_ready is False
    assert gate.blocking_reviews == 1


def test_panel_drills_follow_instance_transforms():
    pcb = PCBGeometry(
        outline=box(0, 0, 40, 30),
        holes=[
            DrillHit("h1", 4, 4, 3.0, False, "T1", "drill"),
            DrillHit("h2", 36, 26, 3.0, False, "T1", "drill"),
        ],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    result = FixtureGenerator({"pcb_geometry": pcb}).generate(
        {"panelEnabled": True, "panelRows": 2, "panelCols": 2, "panelBoardSpacingMm": 3}
    )
    holes = result["fixture_geometry"].pcb.holes
    assert len(holes) == 8
    xs = sorted({round(h.x, 3) for h in holes})
    assert max(xs) - min(xs) > 30


def test_pressure_relief_attaches_to_onboard_pocket():
    body = box(-20, -20, 120, 100)
    pcb = box(0, 0, 80, 70)
    pocket = box(10, 10, 55, 50)
    channels, _ = generate_pressure_relief(
        body=body,
        pcb_outline=pcb,
        keepouts=[pocket],
        keepout_meta=[FixtureRegion("k1", "pocket", pocket, "semantic_component", ("U1",), 0.9, parameters={"pocketDepthMm": 2.0})],
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
    assert any(c.intersects(pocket) for c in channels)


def test_overlay_emits_data_feature():
    svg = overlay_svg(
        ManualFixtureData(fixture_outline=[box(0, 0, 100, 80)], solder_regions=[box(10, 10, 20, 20)]),
        {"fixture_outline": box(0, 0, 100, 80), "solder_windows": [box(10, 10, 20, 20)]},
    )
    assert 'data-feature="solder_openings"' in svg
    assert 'data-feature="fixture_body"' in svg


def test_cannot_approve_from_imported():
    assert can_advance("IMPORTED", "APPROVED") is False
    assert can_advance("VALIDATED", "APPROVED") is True


def test_transform_inverse_with_mirror_and_rotation():
    t = Transform2D(tx=10, ty=4, rotation_deg=90, mirror_x=True)
    gx, gy = t.apply_xy(3, 5)
    bx, by = t.inverse().apply_xy(gx, gy)
    assert abs(bx - 3) < 1e-9
    assert abs(by - 5) < 1e-9
    geom = t.inverse().apply(t.apply(box(0, 0, 2, 1)))
    assert abs(geom.bounds[0] - 0) < 1e-6


def test_sha_changes_when_drc_threshold_param_changes():
    pcb = PCBGeometry(outline=box(0, 0, 80, 60), holes=[], layers=[], source_sha256="s", geometry_sha256="g")
    fixture = FixtureGeometry(
        pcb=pcb,
        body=box(-5, -5, 90, 70),
        sink_region=box(-0.2, -0.2, 80.2, 60.2),
        keepout_regions=[],
        solder_regions=[],
        locating_pins=[],
        locating_pin_candidates=[],
        clamp_holes=[],
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={"minimumMaterialWebMm": 2.0, "palletThicknessMm": 10, "pocketFloorThicknessMm": 2, "defaultPocketDepthMm": 2, "componentVerticalClearanceMm": 0.5},
        geometry_sha256="",
    )
    a = geometry_digest(fixture)
    fixture.parameters["minimumMaterialWebMm"] = 3.5
    b = geometry_digest(fixture)
    assert a != b
