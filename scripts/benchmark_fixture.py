"""Profile parse / semantic / generate / DRC / validation / DXF. Large is feature count, not file size."""
from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from shapely.geometry import box

from app.models.geometry import DrillHit, PCBGeometry
from app.services.exporters.dxf_exporter import export_fixture_dxf
from app.services.fixture.drc import run_drc
from app.services.fixture.generator import FixtureGenerator
from app.services.gerber.parser import GerberParser
from app.services.gerber.semantic_builder import build_semantic_model
from validation.golden_validator import compare_fixture
from validation.manual_dxf_parser import ManualFixtureData


def _time_ms(fn):
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000.0


def _synthetic_pcb(width: float, height: float, pth: int, rows: int = 1, cols: int = 1) -> PCBGeometry:
    holes = []
    holes.append(DrillHit("pin-a", 4, 4, 3.0, False, "T1", "drill"))
    holes.append(DrillHit("pin-b", width - 4, height - 4, 3.0, False, "T1", "drill"))
    for i in range(pth):
        x = 8 + (i * 7) % max(width - 16, 8)
        y = 8 + ((i * 11) % max(height - 16, 8))
        holes.append(DrillHit(f"pth-{i}", x, y, 1.0, True, "T2", "drill"))
    return PCBGeometry(
        outline=box(0, 0, width, height),
        holes=holes,
        layers=[],
        source_sha256="synthetic",
        geometry_sha256="synthetic",
    )


def run_one(label: str, zip_path: Path | None = None, pcb: PCBGeometry | None = None, params: dict | None = None) -> dict:
    tracemalloc.start()
    parse_ms = 0.0
    semantic_ms = 0.0
    if zip_path is not None:
        parser = GerberParser()
        analysis, parse_ms = _time_ms(lambda: parser.parse_zip(str(zip_path)))
        pcb = analysis.get("pcb_geometry")
        if pcb is None:
            tracemalloc.stop()
            return {"label": label, "error": "no pcb geometry", "kind": "zip"}
        _, semantic_ms = _time_ms(lambda: build_semantic_model(pcb))
        kind = "zip"
    else:
        kind = "synthetic_scale"
    gen = FixtureGenerator({"pcb_geometry": pcb})
    fixture, generate_ms = _time_ms(lambda: gen.generate(params or {}))
    geom = fixture["fixture_geometry"]
    _, drc_ms = _time_ms(lambda: run_drc(geom))
    out = ROOT / "backend" / "outputs" / f"bench_{label}.dxf"
    out.parent.mkdir(parents=True, exist_ok=True)
    _, dxf_ms = _time_ms(lambda: export_fixture_dxf(fixture, str(out)))
    _, validation_ms = _time_ms(lambda: compare_fixture(ManualFixtureData(), fixture, label))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    summary = fixture.get("featureSummary") or {}
    return {
        "label": label,
        "kind": kind,
        "zip": str(zip_path) if zip_path else None,
        "parse_ms": round(parse_ms, 2),
        "semantic_ms": round(semantic_ms, 2),
        "fixture_generation_ms": round(generate_ms, 2),
        "drc_ms": round(drc_ms, 2),
        "validation_ms": round(validation_ms, 2),
        "dxf_export_ms": round(dxf_ms, 2),
        "peakMemoryKb": round(peak / 1024.0, 1),
        "geometrySha256": fixture.get("geometrySha256"),
        "pthCount": len([h for h in (pcb.holes or []) if h.plated]),
        "npthCount": len([h for h in (pcb.holes or []) if not h.plated]),
        "components": summary.get("semanticComponentCount"),
        "solderWindows": summary.get("solderWindowCount"),
        "keepouts": summary.get("keepoutRegionCount"),
        "drcPairs": len(fixture.get("issues") or []),
        "panelInstances": summary.get("panelInstanceCount"),
    }


def main():
    rows = [
        run_one("small", ROOT / "backend" / "tests" / "fixtures" / "wave_fixture_outline_drill.zip"),
        run_one("medium", ROOT / "production_samples" / "case_001_standard_demo" / "wave_fixture_outline_drill.zip"),
        run_one("large_zip_not_large_geometry", ROOT / "backend" / "tests" / "fixtures" / "CASE-004_x2_nonstandard_names.zip"),
        run_one("large_synthetic", pcb=_synthetic_pcb(240, 180, pth=180)),
        run_one("large_panel_synthetic", pcb=_synthetic_pcb(80, 60, pth=40), params={"panelEnabled": True, "panelRows": 3, "panelCols": 3, "panelBoardSpacingMm": 3}),
    ]
    print(json.dumps(rows, indent=2))
    return rows


if __name__ == "__main__":
    main()
