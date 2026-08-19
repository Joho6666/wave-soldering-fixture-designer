"""Test DXF dimension annotations."""
import os
import tempfile
import pytest
from shapely.geometry import Polygon, box
from app.services.exporters.dxf_exporter import export_fixture_dxf


def test_dxf_has_dimension_layer():
    layers_data = {
        "pcb_outline": Polygon([(0, 0), (80, 0), (80, 60), (0, 60)]),
        "sink_area": Polygon([(0, 0), (80, 0), (80, 60), (0, 60)]).buffer(0.2),
        "fixture_outline": box(-20, -30, 100, 90),
        "keepout_zones": [],
        "solder_windows": [],
        "pins": [
            {"id": "pin-1", "x": 5, "y": 5, "diameter": 3.0},
            {"id": "pin-2", "x": 75, "y": 55, "diameter": 3.0},
        ],
        "clips": [],
        "handholds": [],
        "rails": [],
        "solder_barriers": [],
        "solder_barrier_mount_holes": [],
        "spring_clips": [],
    }
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        out_path = f.name
    try:
        export_fixture_dxf(layers_data, out_path)
        import ezdxf
        doc = ezdxf.readfile(out_path)
        layer_names = [l.dxf.name for l in doc.layers]
        assert "DIMENSIONS" in layer_names
        assert "SPRING_CLIPS" in layer_names
    finally:
        os.unlink(out_path)