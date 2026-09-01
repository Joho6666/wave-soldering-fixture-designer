from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import box

import importlib.util

from app.models.ai_schemas import AICommandRequest
from validation.case_catalog import list_cases
from validation.feature_thresholds import FEATURE_KEYS, decide_status
from validation.golden_validator import compare_fixture
from validation.lifecycle import append_history
from validation.manual_dxf_parser import CircleFeature, ManualFixtureData
from validation.metrics_aggregate import aggregate
from validation.overrides import apply_overrides, validate_override
from validation.pipeline import generate_fixture_for_case


ROOT = Path(__file__).resolve().parents[2]


def test_five_cases_exist_without_reference_dxf():
    cases = {c["caseId"]: c for c in list_cases()}
    for case_id in ("CASE-001", "CASE-002", "CASE-003", "CASE-004", "CASE-005"):
        item = cases[case_id]
        assert item["hasInput"] is True
        assert item["hasReferenceDxf"] is False
        assert item["status"] in {"awaiting_reference", "awaiting_reference_dxf", "awaiting_input"}
        assert item["status"] != "passed"
        assert item["kind"] == "synthetic_demo"


def test_feature_thresholds_are_not_global_iou():
    assert "locating_pins" in FEATURE_KEYS
    pin_fail = decide_status("locating_pins", {"centroidErrorMm": 3.0, "diameterErrorMm": 1.0})
    opening_warn = decide_status("solder_openings", {"iou": 0.80, "hausdorffMm": 2.0, "areaErrorPercent": 10.0})
    assert pin_fail == "FAIL"
    assert opening_warn in {"WARNING", "FAIL"}


def test_missing_reference_features_are_not_available():
    manual = ManualFixtureData()
    generated = {"fixture_outline": box(0, 0, 10, 10)}
    verdict = compare_fixture(manual, generated, "CASE-EMPTY-REF")
    assert verdict.overall in {"FAIL", "NOT_AVAILABLE"}
    assert verdict.status != "passed"
    body = next(f for f in verdict.features if f.name == "fixture_body")
    assert body.status == "FAIL"


def test_import_cli_does_not_invent_reference(tmp_path, monkeypatch):
    gerber = ROOT / "backend" / "tests" / "fixtures" / "wave_fixture_outline_drill.zip"
    spec = importlib.util.spec_from_file_location(
        "import_validation_case",
        ROOT / "scripts" / "import_validation_case.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "CASES_ROOT", tmp_path)
    case_dir = module.import_case("CASE-008", gerber, description="cli import")
    assert (case_dir / "input" / "gerber.zip").is_file()
    assert list((case_dir / "reference").glob("*.dxf")) == []
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    assert meta["status"] == "awaiting_reference"
    assert meta["hasReference"] is False


def test_override_requires_reason_and_updates_sha():
    from app.models.geometry import DrillHit, PCBGeometry
    from app.services.fixture.generator import FixtureGenerator

    pcb = PCBGeometry(
        outline=box(0, 0, 80, 60),
        holes=[DrillHit("h1", 5, 5, 3.0, False, "T1", "drill"), DrillHit("h2", 75, 55, 3.0, False, "T1", "drill")],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    result = FixtureGenerator({"pcb_geometry": pcb}).generate({})
    old_sha = result["geometrySha256"]
    with pytest.raises(ValueError):
        validate_override({"type": "modify_solder_opening", "featureId": "SO-05", "newGeometry": {"wkt": "POLYGON((0 0,1 0,1 1,0 1,0 0))"}, "reason": "short", "engineer": "a"})
    record = validate_override({
        "type": "modify_solder_opening",
        "featureId": "SO-05",
        "sourceIds": ["J3"],
        "oldGeometrySha": old_sha,
        "newGeometry": {"wkt": "POLYGON((10 10,30 10,30 20,10 20,10 10))"},
        "reason": "connector requires larger solder access",
        "engineer": "qa",
    })
    updated = apply_overrides(result, [record])
    assert updated["geometrySha256"] != old_sha


def test_lifecycle_history_appends():
    history = append_history([], "IMPORTED", "2026-09-01T00:00:00+00:00")
    history = append_history(history, "GENERATED", "2026-09-01T01:00:00+00:00")
    assert [h["status"] for h in history] == ["IMPORTED", "GENERATED"]


def test_metrics_zeros_without_reference():
    stats = aggregate(list_cases())
    assert stats["engineerReferenceCount"] == 0
    assert stats["cncTested"] == 0
    assert stats["assemblyTested"] == 0
    assert stats["waveSolderTested"] == 0
    assert stats["averageFixtureIou"] is None


def test_ai_schema_does_not_include_pass_case_command():
    request = AICommandRequest(userMessage="解释 DRC")
    dumped = request.model_dump()
    assert "mark_passed" not in json.dumps(dumped)


@pytest.mark.parametrize("style", ["easyeda", "jlc", "kicad", "altium", "allegro"])
def test_filename_styles_do_not_hardcode_case_id(style, tmp_path):
    src = ROOT / "backend" / "tests" / "fixtures" / "wave_fixture_outline_drill.zip"
    dest = tmp_path / f"{style}_board.zip"
    dest.write_bytes(src.read_bytes())
    from app.services.gerber.parser import GerberParser
    analysis = GerberParser().parse_zip(str(dest))
    assert analysis.get("pcb_geometry") is not None or analysis.get("requires_layer_confirmation")


def test_generate_case_001_does_not_mark_passed():
    cases = {c["caseId"]: c for c in list_cases()}
    item = cases["CASE-001"]
    generated = generate_fixture_for_case(item)
    assert generated["fixture_data"]["geometrySha256"]
    assert item["hasReferenceDxf"] is False
