"""Tests for component detector."""
import pytest
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

from app.models.geometry import PCBGeometry, DrillHit
from app.services.gerber.component_detector import (
    detect_bot_components,
    detect_through_hole_clusters,
)


def _make_pcb(bot_silk=None, holes=None):
    outline = Polygon([(0, 0), (100, 0), (100, 80), (0, 80)])
    if holes is None:
        holes = []
    return PCBGeometry(
        outline=outline,
        holes=holes,
        layers=[],
        source_sha256="test",
        geometry_sha256="test",
        bottom_silkscreen=bot_silk,
    )


class TestBotComponentDetector:
    def test_detects_components_from_silkscreen(self):
        comp1 = Polygon([(10, 10), (20, 10), (20, 20), (10, 20)])
        comp2 = Polygon([(50, 50), (65, 50), (65, 60), (50, 60)])
        bot_silk = MultiPolygon([comp1, comp2])
        pcb = _make_pcb(bot_silk=bot_silk)

        regions = detect_bot_components(pcb)
        assert len(regions) == 2
        assert regions[0].layer_side == "bottom"
        assert regions[0].area > 0

    def test_empty_silkscreen_returns_empty(self):
        pcb = _make_pcb(bot_silk=None)
        regions = detect_bot_components(pcb)
        assert regions == []

    def test_small_regions_filtered(self):
        tiny = Polygon([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)])
        pcb = _make_pcb(bot_silk=tiny)
        regions = detect_bot_components(pcb)
        assert len(regions) == 0


class TestThroughHoleClustering:
    def test_clusters_nearby_pth(self):
        holes = [
            DrillHit("h1", 10.0, 10.0, 1.0, True, "T1", "drills"),
            DrillHit("h2", 12.0, 10.0, 1.0, True, "T1", "drills"),
            DrillHit("h3", 14.0, 10.0, 1.0, True, "T1", "drills"),
            DrillHit("h4", 80.0, 70.0, 1.0, True, "T2", "drills"),
            DrillHit("h5", 82.0, 70.0, 1.0, True, "T2", "drills"),
        ]
        pcb = _make_pcb(holes=holes)
        clusters = detect_through_hole_clusters(pcb, eps_mm=5.0, min_holes=2)
        assert len(clusters) == 2
        cluster_sizes = sorted([c.hole_count for c in clusters])
        assert cluster_sizes == [2, 3]

    def test_isolated_holes_not_clustered(self):
        holes = [
            DrillHit("h1", 10.0, 10.0, 1.0, True, "T1", "drills"),
            DrillHit("h2", 80.0, 70.0, 1.0, True, "T2", "drills"),
        ]
        pcb = _make_pcb(holes=holes)
        clusters = detect_through_hole_clusters(pcb, eps_mm=5.0, min_holes=3)
        assert len(clusters) == 0

    def test_npth_excluded_from_clustering(self):
        holes = [
            DrillHit("h1", 10.0, 10.0, 3.0, False, "T1", "drills"),
            DrillHit("h2", 12.0, 10.0, 3.0, False, "T1", "drills"),
        ]
        pcb = _make_pcb(holes=holes)
        clusters = detect_through_hole_clusters(pcb, eps_mm=5.0, min_holes=2)
        assert len(clusters) == 0
