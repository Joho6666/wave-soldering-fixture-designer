"""Golden-case validation API. Never invents a reference DXF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from validation.case_catalog import get_case, list_cases
from validation.golden_validator import compare_fixture, overlay_svg, parse_reference_dxf, write_reports

router = APIRouter(prefix="/validation", tags=["validation"])


def _case_dir(case_id: str) -> Path:
    return PROJECT_ROOT / "validation" / "cases" / case_id


@router.get("/cases")
def api_list_cases():
    return {"cases": list_cases()}


@router.get("/cases/{case_id}")
def api_get_case(case_id: str):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    return item


@router.get("/cases/{case_id}/overlay")
def api_overlay(case_id: str):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    overlay_path = _case_dir(case_id) / "report" / "overlay.svg"
    if overlay_path.exists():
        return Response(content=overlay_path.read_text(encoding="utf-8"), media_type="image/svg+xml")
    if not item.get("hasReferenceDxf") or not item.get("hasGeneratedDxf"):
        empty = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
            '<text x="12" y="44" fill="#94a3b8" font-size="14">No reference/generated DXF to overlay</text>'
            "</svg>"
        )
        return Response(content=empty, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="overlay not generated yet")


@router.post("/cases/{case_id}/run")
def api_run_case(case_id: str):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    if not item.get("hasInput"):
        raise HTTPException(status_code=409, detail="awaiting_input: no PCB manufacturing ZIP")
    if not item.get("hasReferenceDxf"):
        raise HTTPException(status_code=409, detail="awaiting_reference_dxf: engineer DXF is missing")

    from app.services.fixture.generator import FixtureGenerator
    from app.services.gerber.parser import GerberParser
    from app.services.gerber.semantic_builder import build_semantic_model
    from app.services.exporters.dxf_exporter import export_fixture_dxf, export_fixture_svg

    case_dir = _case_dir(case_id)
    generated_dir = case_dir / "generated"
    report_dir = case_dir / "report"
    generated_dir.mkdir(parents=True, exist_ok=True)

    parser = GerberParser()
    analysis = parser.parse_zip(item["inputPath"])
    if analysis.get("requires_layer_confirmation"):
        raise HTTPException(status_code=409, detail="layer confirmation required before validation")
    pcb = analysis.pop("pcb_geometry")
    pnp = analysis.pop("_pnp_objects", []) or []
    bom = analysis.pop("_bom_objects", []) or []
    build_semantic_model(pcb, pnp_placements=pnp, bom_rows=bom)
    fixture_data = FixtureGenerator({"pcb_geometry": pcb}).generate(item.get("fixtureParameters") or {})
    export_fixture_dxf(fixture_data, str(generated_dir / "fixture.dxf"))
    export_fixture_svg(fixture_data, str(generated_dir / "preview.svg"))

    mapping = None
    mapping_path = case_dir / "reference" / "manual_layer_mapping.json"
    if not mapping_path.exists():
        mapping_path = case_dir / "expected" / "manual_layer_mapping.json"
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    manual = parse_reference_dxf(Path(item["referencePath"]), mapping)
    verdict = compare_fixture(manual, fixture_data, case_id)
    write_reports(verdict, report_dir)
    svg = overlay_svg(manual, fixture_data)
    (report_dir / "overlay.svg").write_text(svg, encoding="utf-8")
    case_json_path = case_dir / "case.json"
    meta = json.loads(case_json_path.read_text(encoding="utf-8")) if case_json_path.exists() else {"caseId": case_id}
    meta["status"] = verdict.status
    case_json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return verdict.to_dict()
