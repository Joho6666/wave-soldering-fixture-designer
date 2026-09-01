"""Profile parse / semantic / generate / DRC / DXF on available sample sizes."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.services.exporters.dxf_exporter import export_fixture_dxf
from app.services.fixture.drc import run_drc
from app.services.fixture.generator import FixtureGenerator
from app.services.gerber.parser import GerberParser
from app.services.gerber.semantic_builder import build_semantic_model


def _time_ms(fn):
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000.0


def run_one(label: str, zip_path: Path) -> dict:
    parser = GerberParser()
    analysis, parse_ms = _time_ms(lambda: parser.parse_zip(str(zip_path)))
    pcb = analysis.get("pcb_geometry")
    if pcb is None:
        return {"label": label, "error": "no pcb geometry"}
    _, semantic_ms = _time_ms(lambda: build_semantic_model(pcb))
    gen = FixtureGenerator({"pcb_geometry": pcb})
    fixture, generate_ms = _time_ms(lambda: gen.generate({}))
    geom = fixture["fixture_geometry"]
    _, drc_ms = _time_ms(lambda: run_drc(geom))
    out = ROOT / "backend" / "outputs" / f"bench_{label}.dxf"
    out.parent.mkdir(parents=True, exist_ok=True)
    _, dxf_ms = _time_ms(lambda: export_fixture_dxf(fixture, str(out)))
    return {
        "label": label,
        "zip": str(zip_path),
        "parse_ms": round(parse_ms, 2),
        "semantic_ms": round(semantic_ms, 2),
        "fixture_generation_ms": round(generate_ms, 2),
        "drc_ms": round(drc_ms, 2),
        "dxf_export_ms": round(dxf_ms, 2),
        "geometrySha256": fixture.get("geometrySha256"),
        "solderWindows": fixture["featureSummary"].get("solderWindowCount"),
        "keepouts": fixture["featureSummary"].get("keepoutRegionCount"),
    }


def main():
    samples = {
        "small": ROOT / "backend" / "tests" / "fixtures" / "wave_fixture_outline_drill.zip",
        "medium": ROOT / "production_samples" / "case_001_standard_demo" / "wave_fixture_outline_drill.zip",
        "large": ROOT / "backend" / "tests" / "fixtures" / "CASE-004_x2_nonstandard_names.zip",
    }
    rows = []
    for label, path in samples.items():
        if not path.exists():
            rows.append({"label": label, "error": f"missing {path}"})
            continue
        rows.append(run_one(label, path))
    print(json.dumps(rows, indent=2))
    return rows


if __name__ == "__main__":
    main()
