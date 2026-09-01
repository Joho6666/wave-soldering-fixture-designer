"""Load and persist Golden Case metadata without inventing reference DXF files."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CASES_DIR = ROOT / "cases"

DEFAULT_CASE = {
    "caseId": "CASE-001",
    "description": "Standard demo board — placeholder until an engineer provides a reference DXF.",
    "pcbInput": None,
    "referenceDxf": None,
    "fixtureParameters": {},
    "processProfile": {},
    "expectedFeatures": {
        "keepoutCount": None,
        "solderOpeningCount": None,
        "pinCount": 2,
    },
    "status": "awaiting_input",
    "engineer": None,
    "createdAt": "2026-08-31T00:00:00+00:00",
    "notes": "No customer Gerber and no engineer reference DXF. Do not mark passed.",
}


def _case_dirs() -> list[Path]:
    if not CASES_DIR.exists():
        return []
    return sorted(p for p in CASES_DIR.iterdir() if p.is_dir())


def _find_zip(folder: Path) -> Path | None:
    if not folder.exists():
        return None
    zips = list(folder.glob("*.zip"))
    return zips[0] if zips else None


def _find_dxf(folder: Path) -> Path | None:
    if not folder.exists():
        return None
    for name in ("manual_fixture.dxf", "reference.dxf"):
        p = folder / name
        if p.exists():
            return p
    dxfs = list(folder.glob("*.dxf"))
    return dxfs[0] if dxfs else None


def infer_status(case_dir: Path, declared: str | None) -> str:
    input_zip = _find_zip(case_dir / "input") or _find_zip(case_dir / "source")
    ref = _find_dxf(case_dir / "reference") or _find_dxf(case_dir / "expected")
    report = case_dir / "report" / "validation_report.json"
    if declared in {"passed", "failed", "review_required"} and report.exists():
        return declared
    if input_zip is None:
        return "awaiting_input"
    if ref is None:
        return "awaiting_reference_dxf"
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
    payload = {
        "caseId": case_id,
        "description": data.get("description") or DEFAULT_CASE["description"],
        "pcbInput": data.get("pcbInput"),
        "referenceDxf": data.get("referenceDxf"),
        "fixtureParameters": data.get("fixtureParameters") or {},
        "processProfile": data.get("processProfile") or {},
        "expectedFeatures": data.get("expectedFeatures") or data.get("expected") or {},
        "status": infer_status(case_dir, data.get("status")),
        "engineer": data.get("engineer"),
        "createdAt": data.get("createdAt") or datetime.now(timezone.utc).isoformat(),
        "notes": data.get("notes") or "",
        "path": str(case_dir),
    }
    input_zip = _find_zip(case_dir / "input") or _find_zip(case_dir / "source")
    ref = _find_dxf(case_dir / "reference") or _find_dxf(case_dir / "expected")
    generated = case_dir / "generated" / "fixture.dxf"
    report = case_dir / "report" / "validation_report.json"
    payload["hasInput"] = input_zip is not None
    payload["hasReferenceDxf"] = ref is not None
    payload["hasGeneratedDxf"] = generated.exists()
    payload["hasReport"] = report.exists()
    payload["inputPath"] = str(input_zip) if input_zip else None
    payload["referencePath"] = str(ref) if ref else None
    payload["generatedPath"] = str(generated) if generated.exists() else None
    payload["reportPath"] = str(report) if report.exists() else None
    if report.exists():
        try:
            payload["report"] = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload["report"] = None
    else:
        payload["report"] = None
    return payload


def list_cases() -> list[dict[str, Any]]:
    cases = [load_case_json(d) for d in _case_dirs()]
    if not cases:
        return [{**DEFAULT_CASE, "hasInput": False, "hasReferenceDxf": False, "hasGeneratedDxf": False, "hasReport": False, "report": None}]
    return cases


def get_case(case_id: str) -> dict[str, Any] | None:
    for item in list_cases():
        if item["caseId"] == case_id:
            return item
    return None
