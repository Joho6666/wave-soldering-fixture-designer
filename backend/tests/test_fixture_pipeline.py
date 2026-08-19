from pathlib import Path
import subprocess
import sys

import ezdxf
import pytest

from app.services.fixture.generator import FixtureGenerator
from app.services.exporters.dxf_exporter import export_fixture_dxf, export_fixture_svg
from app.services.gerber.parser import GerberParseError, GerberParser


FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"
PARAMETERS = {
    "sinkClearanceMm": 0.2,
    "keepoutClearanceMm": 0.7,
    "solderClearanceMm": 3.0,
    "filletRadiusMm": 1.85,
    "clampHoleDiameterMm": 3.4,
    "clampOffsetMm": 10,
    "handholdWidthMm": 20,
    "handholdHeightMm": 40,
    "handholdOverlapMm": 1,
    "handholdCornerRadiusMm": 2,
    "fixtureMarginXmm": 20,
    "fixtureMarginYmm": 30,
    "fixtureCornerRadiusMm": 5,
    "fixtureSizeRoundStepMm": 10,
    "railWidthMm": 5,
    "solderBarrierWidthMm": 10,
}


def test_parser_returns_real_outline_and_exact_drills():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))

    assert analysis["fileCount"] == 4
    assert analysis["outlineClosed"] is True
    assert analysis["width"] == 25.654
    assert analysis["height"] == 48.26
    assert analysis["holeCount"] == 31
    assert analysis["pthCount"] == 31
    assert analysis["npthCount"] == 0
    assert sorted({hole["diameterMm"] for hole in analysis["holes"]}) == [0.305, 0.915]


def test_sparse_package_requires_review_instead_of_placeholder_features():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    generated = FixtureGenerator(analysis).generate(PARAMETERS)

    assert generated["status"] == "review_required"
    assert generated["featureSummary"]["keepoutRegionCount"] == 0
    assert generated["featureSummary"]["locatingPinCount"] == 0
    assert generated["featureSummary"]["locatingCandidateCount"] == 31
    assert {item["type"] for item in generated["reviewItems"]} >= {
        "bot_keepout_region", "top_solder_region", "locating_pin_candidate"
    }
    assert generated["sink_area"].area > generated["pcb_outline"].area
    assert generated["fixture_outline"].contains(generated["sink_area"])


def test_dxf_and_svg_share_real_fixture_geometry(tmp_path):
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    generated = FixtureGenerator(analysis).generate(PARAMETERS)
    dxf_path = tmp_path / "fixture.dxf"
    svg_path = tmp_path / "preview.svg"

    export_fixture_dxf(generated, str(dxf_path))
    export_fixture_svg(generated, str(svg_path))

    document = ezdxf.readfile(dxf_path)
    assert document.dxfversion == "AC1032"
    assert len(document.modelspace()) > 0
    layer_names = {entity.dxf.layer for entity in document.modelspace()}
    assert {"FIXTURE_OUTLINE", "PCB_OUTLINE", "PCB_DRILL", "SINK_AREA"} <= layer_names

    svg = svg_path.read_text(encoding="utf-8")
    for layer_id in ["fixture-outline", "pcb-outline", "pcb-drill", "sink-region", "locating-pin-candidates"]:
        assert f'id="{layer_id}"' in svg
    assert 'id="keepout-bot"' in svg
    assert 'id="solder-top"' in svg


def test_stable_layer_ids_across_processes():
    backend_dir = str(Path(__file__).parent.parent)
    command = (
        f"import sys; sys.path.insert(0, r'{backend_dir}'); "
        "from app.services.gerber.parser import GerberParser; "
        f"r=GerberParser().parse_zip(r'{FIXTURE_ARCHIVE}'); "
        "print(','.join(layer['id'] for layer in r['layers']))"
    )
    first = subprocess.check_output([sys.executable, "-c", command], text=True, cwd=backend_dir).strip().splitlines()[-1]
    second = subprocess.check_output([sys.executable, "-c", command], text=True, cwd=backend_dir).strip().splitlines()[-1]
    assert first == second


def test_invalid_zip_fails_instead_of_estimating(tmp_path):
    invalid = tmp_path / "invalid.zip"
    invalid.write_text("not a zip", encoding="utf-8")
    with pytest.raises(GerberParseError) as error:
        GerberParser().parse_zip(str(invalid))
    assert error.value.code == "INVALID_ZIP"
