"""Semantic BOT SMD and through-hole classification."""
from shapely.geometry import MultiPolygon, Polygon

from app.models.geometry import DrillHit, PCBGeometry
from app.services.gerber.component_detector import (
    classify_through_hole_group,
    detect_through_hole_components,
)
from app.services.gerber.semantic_builder import build_semantic_model


def _pcb(holes=None, bot_silk=None):
    return PCBGeometry(
        outline=Polygon([(0, 0), (120, 0), (120, 80), (0, 80)]),
        holes=holes or [],
        layers=[],
        source_sha256="t",
        geometry_sha256="t",
        bottom_silkscreen=bot_silk,
    )


def _hit(i, x, y, dia=0.8, plated=True, kind="hole"):
    return DrillHit(f"h{i}", x, y, dia, plated, "T1", "drills", kind)


class TestBotSmdSemantic:
    def test_bot_smd_from_silkscreen(self):
        silk = MultiPolygon([
            Polygon([(10, 10), (18, 10), (18, 16), (10, 16)]),
            Polygon([(40, 40), (52, 40), (52, 48), (40, 48)]),
        ])
        pcb = _pcb(bot_silk=silk)
        build_semantic_model(pcb)
        bottoms = [c for c in pcb.components if c.side == "bottom"]
        assert len(bottoms) == 2
        assert all(c.component_type == "smd" for c in bottoms)
        assert all(c.source == "silkscreen_inference" for c in bottoms)


class TestThroughHoleKinds:
    def test_1xn_header(self):
        holes = [_hit(i, 10 + i * 2.54, 20) for i in range(6)]
        cluster = classify_through_hole_group(holes, "tht-1")
        assert cluster.component_type == "1xn"
        assert cluster.inferred_rows == 1
        assert cluster.inferred_columns >= 5

    def test_2xn_header(self):
        holes = []
        n = 0
        for col in range(5):
            for row in range(2):
                n += 1
                holes.append(_hit(n, 30 + col * 2.54, 40 + row * 2.54))
        cluster = classify_through_hole_group(holes, "tht-2")
        assert cluster.component_type == "2xn"
        assert cluster.inferred_rows == 2

    def test_dip_like(self):
        holes = []
        n = 0
        for col in range(7):
            for row in range(2):
                n += 1
                holes.append(_hit(n, 10 + col * 2.54, 10 + row * 7.62, dia=0.8))
        cluster = classify_through_hole_group(holes, "tht-dip")
        assert cluster.component_type in {"dip", "2xn"}
        assert cluster.inferred_rows == 2
        assert cluster.inferred_columns >= 6

    def test_slot_drill_ignored(self):
        holes = [
            _hit(1, 10, 10, dia=3.0, plated=False, kind="slot"),
            _hit(2, 12, 10, dia=3.0, plated=False, kind="slot"),
            _hit(3, 20, 20, dia=0.9, plated=True, kind="hole"),
            _hit(4, 22.54, 20, dia=0.9, plated=True, kind="hole"),
        ]
        pcb = _pcb(holes=holes)
        comps = detect_through_hole_components(pcb)
        ids = {hid for c in comps for hid in c.hole_ids}
        assert "h1" not in ids
        assert "h2" not in ids
        assert "h3" in ids
        assert "h4" in ids

    def test_isolated_pth_still_emitted(self):
        pcb = _pcb(holes=[_hit(1, 15, 15)])
        comps = detect_through_hole_components(pcb)
        assert len(comps) == 1
        assert comps[0].hole_ids == ("h1",)
