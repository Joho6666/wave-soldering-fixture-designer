"""Fixture manufacturing manifest — traceability for every generation."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.version import ALGORITHM_VERSION, RULE_PROFILE_VERSION, SOFTWARE_VERSION


def file_sha256(path: str | Path | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_fixture_manifest(
    *,
    job_id: str | None,
    fixture_data: dict[str, Any],
    parameters: dict[str, Any] | None,
    input_path: str | Path | None = None,
    dxf_path: str | Path | None = None,
    pcb_info: dict[str, Any] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    overrides: list[dict[str, Any]] | None = None,
    validation_status: str | None = None,
    layer_mapping_confirmed: bool = False,
) -> dict[str, Any]:
    geom = fixture_data.get("fixture_geometry")
    pcb = getattr(geom, "pcb", None) if geom is not None else None
    return {
        "softwareVersion": SOFTWARE_VERSION,
        "algorithmVersion": ALGORITHM_VERSION,
        "rulesVersion": RULE_PROFILE_VERSION,
        "geometrySha256": fixture_data.get("geometrySha256"),
        "inputFileSha256": file_sha256(input_path) or (getattr(pcb, "source_sha256", None) if pcb else None),
        "dxfOutputSha256": file_sha256(dxf_path),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "jobId": job_id,
        "pcb": pcb_info
        or {
            "widthMm": getattr(pcb, "width", None),
            "heightMm": getattr(pcb, "height", None),
            "holeCount": len(getattr(pcb, "holes", []) or []) if pcb else 0,
            "componentCount": len(getattr(pcb, "components", []) or []) if pcb else 0,
        },
        "processProfile": dict(parameters or fixture_data.get("fixture_geometry") and getattr(geom, "parameters", {}) or {}),
        "generatedFeatures": fixture_data.get("featureSummary", {}),
        "drcResults": fixture_data.get("issues", []),
        "engineerReviews": reviews if reviews is not None else fixture_data.get("reviewItems", []),
        "overrides": overrides or [],
        "validationStatus": validation_status or "not_run",
        "layerMappingConfirmed": layer_mapping_confirmed,
        "panel": fixture_data.get("panel"),
        "status": fixture_data.get("status"),
    }
