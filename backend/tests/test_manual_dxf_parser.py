"""Tests for ManualFixtureDxfParser — create synthetic DXF in memory and parse."""
import math
import tempfile
from pathlib import Path

import ezdxf
import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from validation.manual_dxf_parser import ManualFixtureDxfParser, ManualFixtureData


def _create_test_dxf(path: str):
    """Create a minimal DXF with known geometry on standard layers."""
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    doc.layers.new("FIXTURE_OUTLINE")
    doc.layers.new("SINK_AREA")
    doc.layers.new("POSITIONING_PINS")
    doc.layers.new("CLIPS")
    doc.layers.new("KEEPOUT_BOT")

    msp.add_lwpolyline(
        [(0, 0), (100, 0), (100, 80), (0, 80)],
        close=True,
        dxfattribs={"layer": "FIXTURE_OUTLINE"},
    )

    msp.add_lwpolyline(
        [(10, 10), (90, 10), (90, 70), (10, 70)],
        close=True,
        dxfattribs={"layer": "SINK_AREA"},
    )

    msp.add_circle(center=(15, 15), radius=1.5, dxfattribs={"layer": "POSITIONING_PINS"})
    msp.add_circle(center=(85, 65), radius=1.5, dxfattribs={"layer": "POSITIONING_PINS"})

    msp.add_circle(center=(50, 15), radius=1.7, dxfattribs={"layer": "CLIPS"})
    msp.add_circle(center=(50, 65), radius=1.7, dxfattribs={"layer": "CLIPS"})

    msp.add_lwpolyline(
        [(20, 30), (40, 30), (40, 50), (20, 50)],
        close=True,
        dxfattribs={"layer": "KEEPOUT_BOT"},
    )

    doc.saveas(path)


class TestManualFixtureDxfParser:
    def test_parse_basic_dxf(self, tmp_path):
        dxf_path = str(tmp_path / "test.dxf")
        _create_test_dxf(dxf_path)

        parser = ManualFixtureDxfParser()
        result = parser.parse(dxf_path)

        assert isinstance(result, ManualFixtureData)
        assert len(result.fixture_outline) == 1
        assert len(result.sink_region) == 1
        assert len(result.locating_pins) == 2
        assert len(result.clamp_holes) == 2
        assert len(result.keepout_regions) == 1

    def test_fixture_outline_dimensions(self, tmp_path):
        dxf_path = str(tmp_path / "test.dxf")
        _create_test_dxf(dxf_path)

        parser = ManualFixtureDxfParser()
        result = parser.parse(dxf_path)

        outline = result.fixture_outline[0]
        bounds = outline.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        assert width == pytest.approx(100.0, abs=0.01)
        assert height == pytest.approx(80.0, abs=0.01)

    def test_circle_parsing(self, tmp_path):
        dxf_path = str(tmp_path / "test.dxf")
        _create_test_dxf(dxf_path)

        parser = ManualFixtureDxfParser()
        result = parser.parse(dxf_path)

        pin = result.locating_pins[0]
        assert pin.x == pytest.approx(15.0, abs=0.01)
        assert pin.y == pytest.approx(15.0, abs=0.01)
        assert pin.diameter == pytest.approx(3.0, abs=0.01)

    def test_custom_layer_mapping(self, tmp_path):
        doc = ezdxf.new("R2018")
        msp = doc.modelspace()
        doc.layers.new("MY_OUTLINE")
        msp.add_lwpolyline([(0, 0), (50, 0), (50, 30), (0, 30)], close=True, dxfattribs={"layer": "MY_OUTLINE"})
        dxf_path = str(tmp_path / "custom.dxf")
        doc.saveas(dxf_path)

        parser = ManualFixtureDxfParser(layer_mapping={"MY_OUTLINE": "FIXTURE_OUTLINE"})
        result = parser.parse(dxf_path)

        assert len(result.fixture_outline) == 1
        assert len(result.unmapped_layers) == 0

    def test_missing_file_raises(self):
        parser = ManualFixtureDxfParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path.dxf")

    def test_line_entities_polygonize(self, tmp_path):
        doc = ezdxf.new("R2018")
        msp = doc.modelspace()
        doc.layers.new("SINK_AREA")
        msp.add_line((0, 0), (20, 0), dxfattribs={"layer": "SINK_AREA"})
        msp.add_line((20, 0), (20, 15), dxfattribs={"layer": "SINK_AREA"})
        msp.add_line((20, 15), (0, 15), dxfattribs={"layer": "SINK_AREA"})
        msp.add_line((0, 15), (0, 0), dxfattribs={"layer": "SINK_AREA"})
        dxf_path = str(tmp_path / "lines.dxf")
        doc.saveas(dxf_path)

        parser = ManualFixtureDxfParser()
        result = parser.parse(dxf_path)

        assert len(result.sink_region) == 1
        assert result.sink_region[0].area == pytest.approx(300.0, abs=0.1)

    def test_spline_and_ellipse_entities(self, tmp_path):
        doc = ezdxf.new("R2018")
        msp = doc.modelspace()
        doc.layers.new("KEEPOUT_BOT")
        doc.layers.new("SOLDER_TOP")

        # 闭合 Spline
        msp.add_spline([(0, 0), (10, 5), (20, 0), (10, -5), (0, 0)], dxfattribs={"layer": "KEEPOUT_BOT"})
        # 闭合 Ellipse
        msp.add_ellipse((50, 50), (15, 0), ratio=0.6, dxfattribs={"layer": "SOLDER_TOP"})

        dxf_path = str(tmp_path / "complex_entities.dxf")
        doc.saveas(dxf_path)

        parser = ManualFixtureDxfParser()
        result = parser.parse(dxf_path)

        assert len(result.keepout_regions) >= 1
        assert len(result.solder_regions) >= 1
        assert result.keepout_regions[0].area > 0
        assert result.solder_regions[0].area > 0
