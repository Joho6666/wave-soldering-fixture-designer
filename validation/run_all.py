"""CLI entry point: scan validation/cases/, auto-generate fixtures, compare against manual DXF, output reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from validation.manual_dxf_parser import ManualFixtureDxfParser
from validation.geometry_comparator import GeometryComparator


def _auto_generate(gerber_zip_path: Path, output_dir: Path) -> dict | None:
    """Run the backend fixture generation pipeline on a Gerber ZIP and return fixture_data dict."""
    try:
        from app.services.gerber.parser import GerberParser
        from app.services.fixture.generator import FixtureGenerator
        from app.services.exporters.dxf_exporter import export_fixture_dxf, export_fixture_svg

        parser = GerberParser()
        analysis = parser.parse_zip(str(gerber_zip_path))

        if analysis.get("requires_layer_confirmation"):
            print(f"    ⚠ Layer confirmation required — skipping auto-generation")
            return None

        pcb_geom = analysis.get("pcb_geometry")
        if pcb_geom is None:
            print(f"    ⚠ No PCB geometry extracted — skipping")
            return None

        generator = FixtureGenerator({"pcb_geometry": pcb_geom})
        fixture_data = generator.generate({})

        output_dir.mkdir(parents=True, exist_ok=True)
        dxf_path = str(output_dir / "fixture.dxf")
        svg_path = str(output_dir / "preview.svg")
        export_fixture_dxf(fixture_data, dxf_path)
        export_fixture_svg(fixture_data, svg_path)

        return fixture_data

    except Exception as e:
        print(f"    ✗ Auto-generation failed: {e}")
        return None


def run_case(case_dir: Path) -> dict | None:
    """Process a single validation case directory."""
    case_id = case_dir.name
    source_dir = case_dir / "source"
    expected_dir = case_dir / "expected"
    generated_dir = case_dir / "generated"
    report_dir = case_dir / "report"

    gerber_zip = None
    for ext in ("*.zip",):
        candidates = list(source_dir.glob(ext))
        if candidates:
            gerber_zip = candidates[0]
            break

    if gerber_zip is None:
        print(f"  [{case_id}] No gerber.zip in source/ — skipping")
        return None

    print(f"  [{case_id}] Generating fixture from {gerber_zip.name}...")
    fixture_data = _auto_generate(gerber_zip, generated_dir)
    if fixture_data is None:
        return None

    manual_dxf = expected_dir / "manual_fixture.dxf"
    if not manual_dxf.exists():
        print(f"  [{case_id}] No manual_fixture.dxf in expected/ — skipping comparison")
        summary = {"case_id": case_id, "status": "generated_only", "comparison": None}
        report_dir.mkdir(parents=True, exist_ok=True)
        with open(report_dir / "comparison.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return summary

    print(f"  [{case_id}] Parsing manual DXF...")
    try:
        manual_data = ManualFixtureDxfParser.from_case_dir(case_dir)
    except Exception as e:
        print(f"  [{case_id}] ✗ Failed to parse manual DXF: {e}")
        return None

    print(f"  [{case_id}] Comparing geometries...")
    comparator = GeometryComparator()
    report = comparator.full_compare(manual_data, fixture_data, case_id=case_id)

    GeometryComparator.save_report(report, report_dir)
    print(f"  [{case_id}] ✓ Report saved to {report_dir}")

    return report.to_dict()


def main():
    cases_dir = Path(__file__).resolve().parent / "cases"
    if not cases_dir.exists():
        print("No validation/cases/ directory found.")
        sys.exit(1)

    case_dirs = sorted([d for d in cases_dir.iterdir() if d.is_dir()])
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
        print("To add a case, place gerber.zip in validation/cases/CASE-NNN/source/")
        print("Optionally add manual_fixture.dxf in validation/cases/CASE-NNN/expected/")


if __name__ == "__main__":
    main()
