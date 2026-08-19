"""Tests for GeometryComparator — synthetic geometry comparison."""
import math
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from validation.geometry_comparator import (
    GeometryComparator,
    PolygonComparisonResult,
    CircleComparisonResult,
    MultiPolygonComparisonResult,
)
from validation.manual_dxf_parser import CircleFeature


class TestPolygonComparison:
    def test_identical_polygons_iou_1(self):
        comparator = GeometryComparator()
        poly = box(0, 0, 10, 10)
        result = comparator.compare_polygon(poly, poly)
        assert result.iou == pytest.approx(1.0, abs=0.001)
        assert result.hausdorff_distance_mm == pytest.approx(0.0, abs=0.001)
        assert result.area_difference_mm2 == pytest.approx(0.0, abs=0.001)

    def test_offset_polygons_iou_less_than_1(self):
        comparator = GeometryComparator()
        poly_a = box(0, 0, 10, 10)
        poly_b = box(2, 0, 12, 10)
        result = comparator.compare_polygon(poly_a, poly_b)
        assert 0.0 < result.iou < 1.0
        assert result.hausdorff_distance_mm > 0

    def test_non_overlapping_polygons_iou_0(self):
        comparator = GeometryComparator()
        poly_a = box(0, 0, 5, 5)
        poly_b = box(10, 10, 15, 15)
        result = comparator.compare_polygon(poly_a, poly_b)
        assert result.iou == pytest.approx(0.0, abs=0.001)

    def test_none_polygon_returns_default(self):
        comparator = GeometryComparator()
        result = comparator.compare_polygon(None, box(0, 0, 5, 5))
        assert result.iou == 0.0


class TestCircleComparison:
    def test_identical_circles(self):
        comparator = GeometryComparator()
        expected = [CircleFeature(x=10.0, y=20.0, diameter=3.0)]
        generated = [{"x": 10.0, "y": 20.0, "diameter": 3.0}]
        results = comparator.compare_circles(expected, generated)
        assert len(results) == 1
        assert results[0].center_error_mm == pytest.approx(0.0, abs=0.001)
        assert results[0].diameter_error_mm == pytest.approx(0.0, abs=0.001)

    def test_offset_circles(self):
        comparator = GeometryComparator()
        expected = [CircleFeature(x=10.0, y=20.0, diameter=3.0)]
        generated = [{"x": 10.1, "y": 20.2, "diameter": 2.9}]
        results = comparator.compare_circles(expected, generated)
        assert len(results) == 1
        assert results[0].center_error_mm == pytest.approx(math.hypot(0.1, 0.2), abs=0.001)
        assert results[0].diameter_error_mm == pytest.approx(0.1, abs=0.001)

    def test_unmatched_expected(self):
        comparator = GeometryComparator()
        expected = [CircleFeature(x=10.0, y=20.0, diameter=3.0)]
        generated = []
        results = comparator.compare_circles(expected, generated)
        assert len(results) == 1
        assert math.isinf(results[0].center_error_mm)


class TestMultiPolygonComparison:
    def test_identical_sets(self):
        comparator = GeometryComparator()
        polys = [box(0, 0, 5, 5), box(10, 10, 15, 15)]
        result = comparator.compare_multi_polygon(polys, polys)
        assert result.matched_pairs == 2
        assert result.average_iou == pytest.approx(1.0, abs=0.001)
        assert not result.over_segmentation
        assert not result.under_segmentation

    def test_over_segmentation(self):
        comparator = GeometryComparator()
        expected = [box(0, 0, 20, 10)]
        generated = [box(0, 0, 10, 10), box(10, 0, 20, 10)]
        result = comparator.compare_multi_polygon(expected, generated)
        assert result.expected_count == 1
        assert result.generated_count == 2
        assert result.over_segmentation is True

    def test_under_segmentation(self):
        comparator = GeometryComparator()
        expected = [box(0, 0, 10, 10), box(15, 0, 25, 10), box(30, 0, 40, 10)]
        generated = [box(0, 0, 25, 10)]
        result = comparator.compare_multi_polygon(expected, generated)
        assert result.expected_count == 3
        assert result.generated_count == 1
        assert result.under_segmentation is True

    def test_empty_sets(self):
        comparator = GeometryComparator()
        result = comparator.compare_multi_polygon([], [])
        assert result.matched_pairs == 0


class TestReportSerialization:
    def test_save_report(self, tmp_path):
        from validation.geometry_comparator import ComparisonReport
        comparator = GeometryComparator()
        poly = box(0, 0, 10, 10)
        report = ComparisonReport(
            case_id="TEST-001",
            sink_region=comparator.compare_polygon(poly, poly),
        )
        GeometryComparator.save_report(report, tmp_path)
        assert (tmp_path / "comparison.json").exists()
        assert (tmp_path / "comparison.md").exists()

        import json
        with open(tmp_path / "comparison.json") as f:
            data = json.load(f)
        assert data["case_id"] == "TEST-001"
        assert data["sink_region"]["iou"] == pytest.approx(1.0, abs=0.001)
