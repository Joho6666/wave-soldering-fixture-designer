"""Load and persist Golden Case metadata without inventing reference DXF files."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation.lifecycle import infer_lifecycle
from validation.manufacturing import load_feedback
from validation.overrides import list_overrides


ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"


def _case_dirs() -> list[Path]:
    if not CASES_DIR.exists():
        return []
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir() and p.name.startswith("CASE-"))


def _find_zip(folder: Path) -> Path | None:
    if not folder.exists():
        return None
    zips = [p for p in folder.glob("*.zip") if p.is_file()]
    return zips[0] if zips else None


def _find_dxf(folder: Path) -> Path | None:
    if not folder.exists():
        return None
    for name in ("engineer_fixture.dxf", "manual_fixture.dxf", "reference.dxf"):
        p = folder / name
        if p.exists():
            return p
    dxfs = list(folder.glob("*.dxf"))
    return dxfs[0] if dxfs else None


def infer_status(case_dir: Path, declared: str | None) -> str:
    input_zip = _find_zip(case_dir / "input") or _find_zip(case_dir / "source")
    ref = _find_dxf(case_dir / "reference") or _find_dxf(case_dir / "expected")
    report = case_dir / "report" / "validation_report.json"
    if declared in {"passed", "failed", "review_required"} and report.exists() and ref is not None:
        return declared
    if input_zip is None:
        return "awaiting_input"
    if ref is None:
        return "awaiting_reference"
    if report.exists():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            return data.get("status") or "ready"
        except json.JSONDecodeError:
            return "ready"
    return "ready"


def load_case_json(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case.json"
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    case_id = data.get("caseId") or case_dir.name
    input_zip = _find_zip(case_dir / "input") or _find_zip(case_dir / "source")
    ref = _find_dxf(case_dir / "reference") or _find_dxf(case_dir / "expected")
    generated = case_dir / "generated" / "fixture.dxf"
    report = case_dir / "report" / "validation_report.json"
    has_input = input_zip is not None
    has_ref = ref is not None
    has_generated = generated.exists()
    has_report = report.exists()
    status = infer_status(case_dir, data.get("status"))
    lifecycle = infer_lifecycle(
        has_input=has_input,
        has_generated=has_generated,
        has_reference=has_ref,
        has_report=has_report,
        declared=data.get("lifecycle"),
    )
    payload = {
        "caseId": case_id,
        "kind": data.get("kind") or "synthetic_demo",
        "description": data.get("description") or "",
        "pcbInput": data.get("pcbInput"),
        "referenceDxf": data.get("referenceDxf"),
        "fixtureParameters": data.get("fixtureParameters") or {},
        "processProfile": data.get("processProfile") or {},
        "expectedFeatures": data.get("expectedFeatures") or data.get("expected") or {},
        "status": status,
        "lifecycle": lifecycle,
        "history": data.get("history") or [],
        "hasReference": has_ref,
        "engineer": data.get("engineer"),
        "createdAt": data.get("createdAt") or datetime.now(timezone.utc).isoformat(),
        "notes": data.get("notes") or "",
        "path": str(case_dir),
        "hasInput": has_input,
        "hasReferenceDxf": has_ref,
        "hasGeneratedDxf": has_generated,
        "hasReport": has_report,
        "inputPath": str(input_zip) if input_zip else None,
        "referencePath": str(ref) if ref else None,
        "generatedPath": str(generated) if generated.exists() else None,
        "reportPath": str(report) if report.exists() else None,
        "overrides": list_overrides(case_dir),
        "manufacturing": load_feedback(case_dir, case_id),
    }
    if report.exists():
        try:
            payload["report"] = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload["report"] = None
    else:
        payload["report"] = None
    return payload


def list_cases() -> list[dict[str, Any]]:
    return [load_case_json(d) for d in _case_dirs()]


def get_case(case_id: str) -> dict[str, Any] | None:
    for item in list_cases():
        if item["caseId"] == case_id:
            return item
    return None


def save_case_json(case_dir: Path, meta: dict[str, Any]) -> None:
    path = case_dir / "case.json"
    serializable = {k: v for k, v in meta.items() if k not in {"path", "report", "overrides", "manufacturing", "hasInput", "hasReferenceDxf", "hasGeneratedDxf", "hasReport", "inputPath", "referencePath", "generatedPath", "reportPath"}}
    path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
