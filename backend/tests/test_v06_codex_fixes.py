"""Regressions for PR #3 Codex notes. Do not invent golden DXF."""
from __future__ import annotations

from pathlib import Path

from shapely.geometry import Point, box

from app.models.geometry import DrillHit, FixtureGeometry, FixtureRegion, PCBGeometry
from app.services.fixture.drc import run_drc
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.pressure_relief import generate_pressure_relief
from app.services.panel.grid import build_grid_panel
from validation.golden_validator import _union, compare_fixture
from validation.manual_dxf_parser import ManualFixtureData
from validation.run_all import find_input_zip, find_reference_dxf


CASES = Path(__file__).resolve().parents[2] / "validation" / "cases"


def test_run_all_looks_in_input_and_reference_not_only_source(tmp_path: Path, monkeypatch):
    import validation.run_all as run_all

    case_dir = tmp_path / "CASE-CLI"
    (case_dir / "input").mkdir(parents=True)
    (case_dir / "reference").mkdir()
    zip_path = case_dir / "input" / "board.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    monkeypatch.setattr(run_all, "CASES_ROOT", tmp_path.resolve())
    found = find_input_zip(case_dir)
    assert found is not None
    assert found.name == "board.zip"
    assert find_reference_dxf(case_dir) is None


def test_union_keeps_smaller_panel_islands():
    a = box(0, 0, 40, 30)
    b = box(50, 0, 70, 20)
    merged = _union([a, b])
    assert merged is not None
    assert abs(merged.area - (a.area + b.area)) < 1e-6
    assert merged.geom_type == "MultiPolygon"


def test_fixture_outline_scores_both_panel_islands():
    left = box(0, 0, 40, 30)
    right = box(50, 0, 90, 30)
    manual = ManualFixtureData(fixture_outline=[left, right])
    generated = {"fixture_outline": left.union(right)}
    verdict = compare_fixture(manual, generated, "CASE-PANEL-ISLANDS")
    outline = next(f for f in verdict.features if f.name == "fixture_outline")
    assert outline.status == "PASS"
    assert outline.iou is not None and outline.iou > 0.99


def test_tooling_hole_drc_uses_radius_not_center():
    pcb = PCBGeometry(
        outline=box(0, 0, 40, 30),
        holes=[DrillHit("h1", 5, 5, 3.0, False, "T1", "drill"), DrillHit("h2", 35, 25, 3.0, False, "T1", "drill")],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    panel = build_grid_panel(
        pcb,
        {"panelEnabled": True, "panelRows": 2, "panelCols": 2, "panelBoardSpacingMm": 2, "panelOuterMarginMm": 8},
    )
    fixture = FixtureGeometry(
        pcb=pcb,
        body=box(-5, -5, 90, 70),
        sink_region=box(-0.2, -0.2, 82, 62),
        keepout_regions=[],
        solder_regions=[],
        locating_pins=[{"id": "p1", "x": 5, "y": 5, "diameter": 2.9}, {"id": "p2", "x": 35, "y": 25, "diameter": 2.9}],
        locating_pin_candidates=[],
        clamp_holes=[],
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={"minimumMaterialWebMm": 2.0, "palletThicknessMm": 10, "pocketFloorThicknessMm": 2, "solderMinOpeningWidthMm": 1.5, "minPinSeparationMm": 15},
        geometry_sha256="",
        tooling_holes=[{"id": "tool-edge", "x": -4.2, "y": 10, "diameter": 3.0}],
        panel=panel,
    )
    codes = {i["code"] for i in run_drc(fixture) if i["code"] == "TOOLING_HOLE_COLLISION"}
    assert "TOOLING_HOLE_COLLISION" in codes


def test_pressure_relief_channel_stays_attached_to_pocket():
    body = box(-20, -20, 120, 100)
    pcb = box(0, 0, 40, 30)
    pocket = box(50, 20, 110, 80)
    channels, _metas = generate_pressure_relief(
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


def test_panel_fixture_body_covers_panel_envelope():
    pcb = PCBGeometry(
        outline=box(0, 0, 40, 30),
        holes=[DrillHit("h1", 4, 4, 3.0, False, "T1", "drill"), DrillHit("h2", 36, 26, 3.0, False, "T1", "drill")],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    gen = FixtureGenerator({"pcb_geometry": pcb})
    result = gen.generate({"panelEnabled": True, "panelRows": 2, "panelCols": 2, "panelBoardSpacingMm": 3, "panelOuterMarginMm": 8})
    panel_outline = result["fixture_geometry"].panel.outline
    body = result["fixture_outline"]
    assert body.contains(panel_outline) or body.covers(panel_outline)
    for hole in result["tooling_holes"]:
        disk = Point(hole["x"], hole["y"]).buffer(float(hole["diameter"]) / 2.0)
        assert body.contains(disk) or body.covers(disk)


def test_case_001_still_not_passed():
    from validation.case_catalog import list_cases

    case = next(c for c in list_cases() if c["caseId"] == "CASE-001")
    assert case["hasReferenceDxf"] is False
    assert case["status"] != "passed"
