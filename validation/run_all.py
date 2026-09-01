"""CLI entry point: scan validation/cases/, auto-generate fixtures, compare against manual DXF, output reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
CASES_ROOT = (Path(__file__).resolve().parent / "cases").resolve()

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from validation.case_catalog import load_case_json
from validation.golden_validator import compare_fixture, overlay_svg, parse_reference_dxf, write_reports


def _confine(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes allowed directory: {path}") from exc
    return resolved


def find_input_zip(case_dir: Path) -> Path | None:
    """Prefer input/, fall back to legacy source/."""
    case_dir = _confine(case_dir, CASES_ROOT)
    for name in ("input", "source"):
        folder = _confine(case_dir / name, case_dir)
        if not folder.exists():
            continue
        zips = sorted(p for p in folder.glob("*.zip") if p.is_file())
        if zips:
            return zips[0]
    return None


def find_reference_dxf(case_dir: Path) -> Path | None:
    """Prefer reference/, fall back to legacy expected/. Never invent a DXF."""
    case_dir = _confine(case_dir, CASES_ROOT)
    for name in ("reference", "expected"):
        folder = _confine(case_dir / name, case_dir)
        if not folder.exists():
            continue
        for filename in ("engineer_fixture.dxf", "manual_fixture.dxf", "reference.dxf"):
            candidate = folder / filename
            if candidate.is_file():
                return _confine(candidate, case_dir)
        dxfs = sorted(p for p in folder.glob("*.dxf") if p.is_file())
        if dxfs:
            return dxfs[0]
    return None


def find_layer_mapping(case_dir: Path) -> dict | None:
    case_dir = _confine(case_dir, CASES_ROOT)
    for name in ("reference", "expected"):
        mapping_path = case_dir / name / "manual_layer_mapping.json"
        if mapping_path.is_file():
            return json.loads(_confine(mapping_path, case_dir).read_text(encoding="utf-8"))
    return None


def _auto_generate(gerber_zip_path: Path, output_dir: Path, fixture_parameters: dict | None = None) -> dict | None:
    """Run the backend fixture generation pipeline on a Gerber ZIP and return fixture_data dict."""
    try:
        from app.services.gerber.parser import GerberParser
        from app.services.gerber.semantic_builder import build_semantic_model
        from app.services.fixture.generator import FixtureGenerator
        from app.services.exporters.dxf_exporter import export_fixture_dxf, export_fixture_svg

        parser = GerberParser()
        analysis = parser.parse_zip(str(gerber_zip_path))

        if analysis.get("requires_layer_confirmation"):
            print("    ⚠ Layer confirmation required — skipping auto-generation")
            return None

        pcb_geom = analysis.get("pcb_geometry")
        if pcb_geom is None:
            print("    ⚠ No PCB geometry extracted — skipping")
            return None

        pnp = analysis.pop("_pnp_objects", []) or []
        bom = analysis.pop("_bom_objects", []) or []
        build_semantic_model(pcb_geom, pnp_placements=pnp, bom_rows=bom)

        generator = FixtureGenerator({"pcb_geometry": pcb_geom})
        fixture_data = generator.generate(fixture_parameters or {})

        output_dir.mkdir(parents=True, exist_ok=True)
        export_fixture_dxf(fixture_data, str(output_dir / "fixture.dxf"))
        export_fixture_svg(fixture_data, str(output_dir / "preview.svg"))
        return fixture_data

    except Exception as e:
        print(f"    ✗ Auto-generation failed: {e}")
        return None


def _write_case_status(case_dir: Path, status: str) -> None:
    case_dir = _confine(case_dir, CASES_ROOT)
    case_json_path = _confine(case_dir / "case.json", case_dir)
    meta: dict = {}
    if case_json_path.is_file():
        try:
            meta = json.loads(case_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta["caseId"] = meta.get("caseId") or case_dir.name
    meta["status"] = status
    case_json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_case(case_dir: Path) -> dict | None:
    """Process a single validation case directory."""
    case_dir = _confine(case_dir, CASES_ROOT)
    case_id = case_dir.name
    catalog = load_case_json(case_dir)
    generated_dir = _confine(case_dir / "generated", case_dir)
    report_dir = _confine(case_dir / "report", case_dir)

    gerber_zip = find_input_zip(case_dir)
    if gerber_zip is None:
        print(f"  [{case_id}] No gerber.zip in input/ (or legacy source/) — skipping")
        _write_case_status(case_dir, "awaiting_input")
        return None

    print(f"  [{case_id}] Generating fixture from {gerber_zip.name}...")
    fixture_data = _auto_generate(gerber_zip, generated_dir, catalog.get("fixtureParameters") or {})
    if fixture_data is None:
        return None

    manual_dxf = find_reference_dxf(case_dir)
    if manual_dxf is None:
        print(f"  [{case_id}] No engineer DXF in reference/ (or legacy expected/) — awaiting_reference_dxf")
        summary = {"case_id": case_id, "status": "awaiting_reference_dxf", "comparison": None}
        report_dir.mkdir(parents=True, exist_ok=True)
        comparison_path = _confine(report_dir / "comparison.json", case_dir)
        comparison_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        _write_case_status(case_dir, "awaiting_reference_dxf")
        return summary

    print(f"  [{case_id}] Parsing manual DXF...")
    try:
        mapping = find_layer_mapping(case_dir)
        manual_data = parse_reference_dxf(manual_dxf, mapping)
    except Exception as e:
        print(f"  [{case_id}] ✗ Failed to parse manual DXF: {e}")
        return None

    print(f"  [{case_id}] Comparing geometries...")
    verdict = compare_fixture(manual_data, fixture_data, case_id)
    write_reports(verdict, report_dir)
    overlay_path = _confine(report_dir / "overlay.svg", case_dir)
    overlay_path.write_text(overlay_svg(manual_data, fixture_data), encoding="utf-8")
    _write_case_status(case_dir, verdict.status)
    print(f"  [{case_id}] ✓ Report saved to {report_dir} overall={verdict.overall}")
    return verdict.to_dict()


def main():
    if not CASES_ROOT.exists():
        print("No validation/cases/ directory found.")
        sys.exit(1)

    case_dirs = sorted(d for d in CASES_ROOT.iterdir() if d.is_dir())
    if not case_dirs:
        print("No cases found in validation/cases/")
        sys.exit(0)

    print(f"Found {len(case_dirs)} validation case(s)\n")

    all_results = []
    for case_dir in case_dirs:
        result = run_case(case_dir)
        if result is not None:
            all_results.append(result)
        print()

    print("=" * 60)
    print(f"Completed: {len(all_results)} / {len(case_dirs)} cases")
    if not all_results:
        print("No cases produced comparison results.")
        print("To add a case, place gerber.zip in validation/cases/CASE-NNN/input/")
        print("Optionally add engineer_fixture.dxf in validation/cases/CASE-NNN/reference/")
        print("Do not copy generated DXF into reference/.")


if __name__ == "__main__":
    main()
