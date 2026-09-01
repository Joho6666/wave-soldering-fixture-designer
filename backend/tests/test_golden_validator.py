import json
from pathlib import Path

from shapely.geometry import box

from validation.case_catalog import infer_status, list_cases, load_case_json
from validation.golden_validator import compare_fixture, overlay_svg, write_reports
from validation.manual_dxf_parser import CircleFeature, ManualFixtureData


def test_identical_fixture_is_pass(tmp_path: Path):
    outline = box(0, 0, 100, 80)
    sink = box(10, 10, 90, 70)
    keep = box(20, 20, 30, 30)
    solder = box(40, 40, 55, 50)
    manual = ManualFixtureData(
        fixture_outline=[outline],
        sink_region=[sink],
        keepout_regions=[keep],
        solder_regions=[solder],
        rails=[box(0, 75, 100, 80)],
        solder_barriers=[box(0, 10, 8, 70)],
        locating_pins=[CircleFeature(5, 5, 3.0)],
        clamp_holes=[CircleFeature(10, 85, 3.4)],
        spring_clips=[CircleFeature(50, 40, 4.9)],
    )
    generated = {
        "fixture_outline": outline,
        "sink_area": sink,
        "keepout_zones": [keep],
        "solder_windows": [solder],
        "rails": [box(0, 75, 100, 80)],
        "solder_barriers": [box(0, 10, 8, 70)],
        "pins": [{"x": 5, "y": 5, "diameter": 3.0}],
        "clips": [{"x": 10, "y": 85, "diameter": 3.4}],
        "spring_clips": [{"x": 50, "y": 40, "diameter": 4.9}],
    }
    verdict = compare_fixture(manual, generated, "CASE-SYN")
    assert verdict.overall == "PASS"
    assert {f.name: f.status for f in verdict.features}["fixture_body"] == "PASS"
    write_reports(verdict, tmp_path)
    assert (tmp_path / "validation_report.json").exists()
    assert (tmp_path / "validation_report.md").exists()
    data = json.loads((tmp_path / "validation_report.json").read_text(encoding="utf-8"))
    assert data["overall"] == "PASS"
    svg = overlay_svg(manual, generated)
    assert 'id="generated"' in svg
    assert 'id="reference"' in svg
    assert 'id="difference"' in svg


def test_shifted_window_is_not_pass():
    manual = ManualFixtureData(
        fixture_outline=[box(0, 0, 100, 80)],
        solder_regions=[box(10, 10, 30, 20)],
    )
    generated = {
        "fixture_outline": box(0, 0, 100, 80),
        "solder_windows": [box(60, 50, 90, 70)],
    }
    verdict = compare_fixture(manual, generated, "CASE-SHIFT")
    solder = next(f for f in verdict.features if f.name == "solder_openings")
    assert solder.status in {"FAIL", "WARNING"}
    assert verdict.overall in {"FAIL", "WARNING"}


def test_case_001_is_awaiting_real_reference():
    cases = list_cases()
    case = next(c for c in cases if c["caseId"] == "CASE-001")
    assert case["hasReferenceDxf"] is False
    assert case["status"] in {"awaiting_input", "awaiting_reference", "awaiting_reference_dxf"}
    root = Path(__file__).resolve().parents[2] / "validation" / "cases" / "CASE-001"
    loaded = load_case_json(root)
    assert infer_status(root, loaded.get("status")) != "passed"
