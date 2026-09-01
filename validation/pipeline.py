"""Generate / revalidate a case without inventing reference DXF."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from validation.case_catalog import load_case_json, save_case_json
from validation.golden_validator import compare_fixture, overlay_svg, parse_reference_dxf, write_reports
from validation.lifecycle import append_history
from validation.overrides import apply_overrides, list_overrides

CASE_ID_RE = re.compile(r"^CASE-[A-Za-z0-9_-]{1,32}$")
CASES_ROOT = Path(__file__).resolve().parent / "cases"


def confined_case_dir(case_id: str) -> Path:
    if not CASE_ID_RE.match(case_id):
        raise ValueError("invalid case id")
    root = CASES_ROOT.resolve()
    path = (root / case_id).resolve()
    path.relative_to(root)
    return path


def generate_fixture_for_case(item: dict[str, Any]) -> dict[str, Any]:
    from app.services.exporters.dxf_exporter import export_fixture_dxf, export_fixture_svg
    from app.services.fixture.generator import FixtureGenerator
    from app.services.fixture.manifest import build_fixture_manifest
    from app.services.gerber.parser import GerberParser
    from app.services.gerber.semantic_builder import build_semantic_model

    case_dir = confined_case_dir(item["caseId"])
    generated_dir = case_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    parser = GerberParser()
    analysis = parser.parse_zip(item["inputPath"])
    pcb = analysis.get("pcb_geometry")
    if pcb is None:
        raise RuntimeError("no PCB geometry")
    pnp = analysis.pop("_pnp_objects", []) or []
    bom = analysis.pop("_bom_objects", []) or []
    build_semantic_model(pcb, pnp_placements=pnp, bom_rows=bom)
    fixture_data = FixtureGenerator({"pcb_geometry": pcb}).generate(item.get("fixtureParameters") or {})
    overrides = list_overrides(case_dir)
    if overrides:
        fixture_data = apply_overrides(fixture_data, overrides)
    dxf_path = generated_dir / "fixture.dxf"
    svg_path = generated_dir / "preview.svg"
    export_fixture_dxf(fixture_data, str(dxf_path))
    export_fixture_svg(fixture_data, str(svg_path))
    manifest = build_fixture_manifest(
        job_id=item["caseId"],
        fixture_data=fixture_data,
        parameters=item.get("fixtureParameters") or {},
        input_path=item.get("inputPath"),
        dxf_path=dxf_path,
        overrides=overrides,
        validation_status="awaiting_reference" if not item.get("hasReferenceDxf") else "not_run",
        layer_mapping_confirmed=not analysis.get("requires_layer_confirmation", False),
    )
    (generated_dir / "fixture_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "fixture_data": fixture_data,
        "analysis": analysis,
        "manifest": manifest,
        "requires_layer_confirmation": bool(analysis.get("requires_layer_confirmation")),
        "case_dir": case_dir,
    }


def write_awaiting_metrics(case_dir: Path, case_id: str, fixture_data: dict[str, Any]) -> None:
    report_dir = case_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = fixture_data.get("featureSummary") or {}
    metrics = {
        "caseId": case_id,
        "status": "awaiting_reference",
        "overall": "NOT_AVAILABLE",
        "reason": "engineer reference DXF is missing; metrics are not comparable",
        "generatedFeatures": summary,
        "iou": None,
        "hausdorffMm": None,
    }
    (report_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    svg = overlay_svg_generated_only(fixture_data)
    (report_dir / "overlay.svg").write_text(svg, encoding="utf-8")


def overlay_svg_generated_only(generated: dict[str, Any]) -> str:
    geom = generated.get("fixture_outline") or generated.get("sink_area")
    if geom is None or getattr(geom, "is_empty", False):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 80">'
            '<text x="12" y="44" fill="#94a3b8" font-size="14">awaiting engineer DXF</text></svg>'
        )
    minx, miny, maxx, maxy = geom.bounds
    pad = 8
    geoms = list(geom.geoms) if geom.geom_type in {"MultiPolygon", "GeometryCollection"} else [geom]
    parts = []
    for g in geoms:
        if g.geom_type != "Polygon":
            continue
        coords = " ".join(f"{x:.3f},{y:.3f}" for x, y in g.exterior.coords)
        parts.append(f'<polygon points="{coords}" fill="#3b82f6" fill-opacity="0.35" stroke="#3b82f6" stroke-width="0.3"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx-pad} {miny-pad} {maxx-minx+2*pad} {maxy-miny+2*pad}">'
        f'<g id="generated" data-layer="generated">{"".join(parts)}</g>'
        f'<g id="reference" data-layer="reference"></g>'
        f'<g id="difference" data-layer="difference"></g>'
        "</svg>"
    )


def persist_generated_lifecycle(case_dir: Path, item: dict[str, Any], *, compared: bool, overall: str | None = None) -> dict[str, Any]:
    meta_path = case_dir / "case.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"caseId": item["caseId"]}
    history = list(meta.get("history") or [])
    history = append_history(history, "PARSED")
    history = append_history(history, "GENERATED")
    if compared and item.get("hasReferenceDxf"):
        history = append_history(history, "REFERENCE_AVAILABLE")
        if overall == "PASS":
            history = append_history(history, "VALIDATED")
            meta["lifecycle"] = "VALIDATED"
        else:
            meta["lifecycle"] = "ENGINEER_REVIEW"
        if item.get("status"):
            meta["status"] = item["status"]
    else:
        meta["lifecycle"] = "GENERATED"
        meta["status"] = "awaiting_reference"
    meta["history"] = history
    save_case_json(case_dir, meta)
    return load_case_json(case_dir)
