"""Golden-case validation API. Never invents a reference DXF."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from validation.case_catalog import get_case, list_cases, load_case_json
from validation.golden_validator import compare_fixture, overlay_svg, parse_reference_dxf, write_reports
from validation.lifecycle import append_history, can_advance
from validation.manufacturing import load_feedback, write_feedback
from validation.overrides import save_override, validate_override
from validation.pipeline import (
    confined_case_dir,
    generate_fixture_for_case,
    persist_generated_lifecycle,
    write_awaiting_metrics,
)

router = APIRouter(prefix="/validation", tags=["validation"])


class OverrideRequest(BaseModel):
    type: str
    featureId: str
    sourceIds: list[str] = Field(default_factory=list)
    oldGeometrySha: str | None = None
    newGeometry: dict
    reason: str
    engineer: str


class LifecycleRequest(BaseModel):
    status: str
    note: str | None = None


class ManufacturingRequest(BaseModel):
    cnc: dict | None = None
    assembly: dict | None = None
    waveSolder: dict | None = None
    issues: list | None = None


def _case_dir(case_id: str) -> Path:
    try:
        return confined_case_dir(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cases")
def api_list_cases():
    return {"cases": list_cases()}


@router.get("/metrics")
def api_metrics():
    from validation.metrics_aggregate import aggregate

    return aggregate(list_cases())


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
    empty = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80">'
        '<text x="12" y="44" fill="#94a3b8" font-size="14">awaiting engineer DXF</text></svg>'
    )
    return Response(content=empty, media_type="image/svg+xml")


@router.post("/cases/{case_id}/regenerate")
def api_regenerate(case_id: str):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    if not item.get("hasInput"):
        raise HTTPException(status_code=409, detail="awaiting_input: no PCB manufacturing ZIP")
    try:
        generated = generate_fixture_for_case(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"generation failed: {exc}") from exc
    case_dir = generated["case_dir"]
    fixture_data = generated["fixture_data"]
    if generated["requires_layer_confirmation"]:
        persist_generated_lifecycle(case_dir, item, compared=False)
        return {"status": "awaiting_reference", "lifecycle": "GENERATED", "layerConfirmation": True, "passed": False}

    if not item.get("hasReferenceDxf"):
        write_awaiting_metrics(case_dir, case_id, fixture_data)
        updated = persist_generated_lifecycle(case_dir, item, compared=False)
        return {
            "status": "awaiting_reference",
            "overall": "NOT_AVAILABLE",
            "lifecycle": updated.get("lifecycle"),
            "geometrySha256": fixture_data.get("geometrySha256"),
            "passed": False,
        }

    mapping = None
    mapping_path = case_dir / "reference" / "manual_layer_mapping.json"
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    manual = parse_reference_dxf(Path(item["referencePath"]), mapping)
    verdict = compare_fixture(manual, fixture_data, case_id)
    report_dir = case_dir / "report"
    write_reports(verdict, report_dir)
    (report_dir / "overlay.svg").write_text(overlay_svg(manual, fixture_data), encoding="utf-8")
    (report_dir / "metrics.json").write_text(json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    meta["status"] = verdict.status
    persist_generated_lifecycle(case_dir, {**item, **meta, "hasReferenceDxf": True}, compared=True)
    payload = verdict.to_dict()
    payload["passed"] = verdict.overall == "PASS"
    return payload


@router.post("/cases/{case_id}/run")
def api_run_case(case_id: str):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    if not item.get("hasInput"):
        raise HTTPException(status_code=409, detail="awaiting_input: no PCB manufacturing ZIP")
    if not item.get("hasReferenceDxf"):
        raise HTTPException(status_code=409, detail="awaiting_reference: engineer DXF is missing")
    return api_regenerate(case_id)


@router.post("/cases/{case_id}/overrides")
def api_add_override(case_id: str, body: OverrideRequest):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    try:
        record = validate_override(body.model_dump())
        path = save_override(_case_dir(case_id), record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    meta_path = _case_dir(case_id) / "case.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"caseId": case_id}
    meta["history"] = append_history(meta.get("history") or [], "ENGINEER_REVIEW")
    meta["lifecycle"] = "ENGINEER_REVIEW"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    regenerated = api_regenerate(case_id)
    return {"override": record, "path": str(path), "regenerated": regenerated}


@router.post("/cases/{case_id}/lifecycle")
def api_lifecycle(case_id: str, body: LifecycleRequest):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    if not can_advance(item.get("lifecycle") or "IMPORTED", body.status):
        raise HTTPException(status_code=409, detail="illegal lifecycle transition")
    if body.status in {"VALIDATED", "APPROVED"} and not item.get("hasReferenceDxf"):
        raise HTTPException(status_code=409, detail="cannot validate or approve without engineer DXF")
    case_dir = _case_dir(case_id)
    meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    meta["lifecycle"] = body.status
    meta["history"] = append_history(meta.get("history") or [], body.status)
    if body.note:
        meta["notes"] = ((meta.get("notes") or "") + "\n" + body.note).strip()
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return load_case_json(case_dir)


@router.post("/cases/{case_id}/manufacturing")
def api_manufacturing(case_id: str, body: ManufacturingRequest):
    item = get_case(case_id)
    if item is None:
        raise HTTPException(status_code=404, detail="validation case not found")
    case_dir = _case_dir(case_id)
    current = load_feedback(case_dir, case_id)
    if body.cnc:
        current["cnc"].update(body.cnc)
    if body.assembly:
        current["assembly"].update(body.assembly)
    if body.waveSolder:
        current["waveSolder"].update(body.waveSolder)
    if body.issues is not None:
        current["issues"] = body.issues
    write_feedback(case_dir, current)
    return current
