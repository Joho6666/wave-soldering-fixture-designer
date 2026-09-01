"""Physical manufacturing feedback. Missing trials stay false/null — never invented."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EMPTY_FEEDBACK = {
    "caseId": None,
    "cnc": {"tested": False, "material": None, "thicknessMm": None, "toolDiameterMm": None, "result": None},
    "assembly": {"tested": False, "pcbFit": None, "pinFit": None, "componentCollision": None},
    "waveSolder": {"tested": False, "result": None},
    "issues": [],
}


def default_feedback(case_id: str) -> dict[str, Any]:
    payload = json.loads(json.dumps(EMPTY_FEEDBACK))
    payload["caseId"] = case_id
    return payload


def load_feedback(case_dir: Path, case_id: str) -> dict[str, Any]:
    path = case_dir / "manufacturing_feedback.json"
    if not path.is_file():
        return default_feedback(case_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_feedback(case_id)
    base = default_feedback(case_id)
    for key in ("cnc", "assembly", "waveSolder"):
        if isinstance(data.get(key), dict):
            base[key].update(data[key])
    if isinstance(data.get("issues"), list):
        base["issues"] = data["issues"]
    base["caseId"] = data.get("caseId") or case_id
    return base


def write_feedback(case_dir: Path, payload: dict[str, Any]) -> Path:
    path = case_dir / "manufacturing_feedback.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def physical_counts(feedbacks: list[dict[str, Any]]) -> dict[str, int]:
    cnc = sum(1 for f in feedbacks if (f.get("cnc") or {}).get("tested") is True)
    assembly = sum(1 for f in feedbacks if (f.get("assembly") or {}).get("tested") is True)
    wave = sum(1 for f in feedbacks if (f.get("waveSolder") or {}).get("tested") is True)
    return {"cncTested": cnc, "assemblyTested": assembly, "waveSolderTested": wave}
