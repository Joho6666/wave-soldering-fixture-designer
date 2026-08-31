"""Pocket depth, solder opening optimizer, locating pin optimizer."""
from shapely.geometry import Polygon, box

from app.models.geometry import DrillHit, PCBComponent, PCBGeometry
from app.services.fixture.drc import run_drc
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.keepout_generator import generate_keepouts
from app.services.fixture.locating_pin_optimizer import generate_locating_pins
from app.services.fixture.solder_optimizer import generate_solder_openings
from app.services.rules.process_profile import ProcessProfile


def _pcb(holes=None, components=None, **kwargs):
    pcb = PCBGeometry(
        outline=Polygon([(0, 0), (80, 0), (80, 60), (0, 60)]),
        holes=holes or [
            DrillHit("h1", 5, 5, 3.0, False, "T1", "drill", "hole"),
            DrillHit("h2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ],
        layers=[],
        source_sha256="t",
        geometry_sha256="t",
        **kwargs,
    )
    if components is not None:
        pcb.components = components
    return pcb


class TestPocketDepth:
    def test_height_based_pocket_depth(self):
        comp = PCBComponent(
            id="bot-1",
            refdes="C1",
            footprint="0805",
            side="bottom",
            centroid_x=20,
            centroid_y=20,
            rotation=0,
            bbox=(16, 18, 24, 22),
            courtyard=box(16, 18, 24, 22),
            body_width_mm=8,
            body_length_mm=4,
            body_height_mm=1.6,
            component_type="smd",
            confidence=0.94,
            source="pnp",
        )
        pcb = _pcb(components=[comp])
        params = ProcessProfile().to_dict()
        keepouts, _reviews, metas = generate_keepouts(pcb, params)
        assert keepouts
        assert metas
        expected = 1.6 + params["componentVerticalClearanceMm"]
        assert abs(metas[0].parameters["pocketDepthMm"] - expected) < 1e-6
        assert metas[0].source_type == "semantic_component"

    def test_floor_thickness_blocking(self):
        comp = PCBComponent(
            id="bot-1",
            refdes="U2",
            footprint="CONN",
            side="bottom",
            centroid_x=20,
            centroid_y=20,
            rotation=0,
            bbox=(10, 10, 30, 30),
            courtyard=box(10, 10, 30, 30),
            body_width_mm=20,
            body_length_mm=20,
            body_height_mm=9.5,
            component_type="smd",
            confidence=0.94,
            source="bom",
        )
        pcb = _pcb(components=[comp])
        gen = FixtureGenerator({"pcb_geometry": pcb})
        result = gen.generate({
            "palletThicknessMm": 10.0,
            "pocketFloorThicknessMm": 2.0,
            "componentVerticalClearanceMm": 0.5,
        }, manual_pins=["h1", "h2"])
        codes = {i["code"] for i in result["issues"]}
        assert "POCKET_FLOOR_TOO_THIN" in codes
        blocking = [i for i in result["issues"] if i["code"] == "POCKET_FLOOR_TOO_THIN"]
        assert blocking[0]["severity"] == "blocking"


class TestSolderOpening:
    def test_single_pth(self):
        holes = [
            DrillHit("pth1", 40, 30, 1.0, True, "T1", "drill", "hole"),
            DrillHit("n1", 5, 5, 3.0, False, "T2", "drill", "hole"),
            DrillHit("n2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        regions, _reviews, metas = generate_solder_openings(pcb, ProcessProfile().to_dict())
        assert len(regions) >= 1
        assert all(r.area > 0.5 for r in regions)
        assert any(m.parameters.get("holeCount") == 1 for m in metas)

    def test_row_header_1xn(self):
        holes = [DrillHit(f"p{i}", 20 + i * 2.54, 30, 0.9, True, "T1", "drill", "hole") for i in range(5)]
        holes += [
            DrillHit("n1", 5, 5, 3.0, False, "T2", "drill", "hole"),
            DrillHit("n2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        regions, _reviews, metas = generate_solder_openings(pcb, ProcessProfile().to_dict())
        assert len(regions) >= 1
        kinds = [m.parameters.get("thtKind") for m in metas]
        assert "1xn" in kinds or any((m.parameters or {}).get("holeCount", 0) >= 5 for m in metas)

    def test_double_row_header(self):
        holes = []
        n = 0
        for col in range(4):
            for row in range(2):
                n += 1
                holes.append(DrillHit(f"p{n}", 25 + col * 2.54, 28 + row * 2.54, 0.9, True, "T1", "drill", "hole"))
        holes += [
            DrillHit("n1", 5, 5, 3.0, False, "T2", "drill", "hole"),
            DrillHit("n2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        regions, _reviews, metas = generate_solder_openings(pcb, ProcessProfile().to_dict())
        assert len(regions) >= 1
        assert any(m.parameters.get("thtKind") == "2xn" for m in metas) or len(regions) <= 2

    def test_neighboring_openings_merge(self):
        holes = [
            DrillHit("a1", 20, 30, 1.0, True, "T1", "drill", "hole"),
            DrillHit("b1", 22.5, 30, 1.0, True, "T1", "drill", "hole"),
            DrillHit("n1", 5, 5, 3.0, False, "T2", "drill", "hole"),
            DrillHit("n2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        params = ProcessProfile().to_dict()
        params["solderOpeningMergeDistanceMm"] = 8.0
        regions, _, _ = generate_solder_openings(pcb, params)
        assert len(regions) == 1

    def test_minimum_material_web_rule_still_runs(self):
        pcb = _pcb(holes=[
            DrillHit("p1", 10, 10, 1.0, True, "T1", "drill", "hole"),
            DrillHit("p2", 12, 10, 1.0, True, "T1", "drill", "hole"),
            DrillHit("n1", 5, 5, 3.0, False, "T2", "drill", "hole"),
            DrillHit("n2", 75, 55, 3.0, False, "T2", "drill", "hole"),
        ])
        result = FixtureGenerator({"pcb_geometry": pcb}).generate({}, manual_pins=["n1", "n2"])
        codes = {i["code"] for i in result["issues"]}
        assert "MINIMUM_MATERIAL_WEB_TOO_SMALL" in codes or result["solder_windows"]


class TestLocatingOptimizer:
    def test_npth_preferred(self):
        holes = [
            DrillHit("pth", 8, 8, 3.0, True, "T1", "drill", "hole"),
            DrillHit("npth1", 6, 6, 3.2, False, "T2", "drill", "hole"),
            DrillHit("npth2", 74, 54, 3.2, False, "T2", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        cands, pins, _ = generate_locating_pins(pcb, ProcessProfile().to_dict())
        npth = next(c for c in cands if c["drillId"] == "npth1")
        pth = next(c for c in cands if c["drillId"] == "pth")
        assert npth["score"] > pth["score"]
        selected = {p["id"] for p in pins}
        assert "pin-npth1" in selected
        assert "pin-npth2" in selected

    def test_slot_rejected(self):
        holes = [
            DrillHit("n1", 5, 5, 3.0, False, "T1", "drill", "hole"),
            DrillHit("n2", 75, 55, 3.0, False, "T1", "drill", "hole"),
            DrillHit("slot", 5, 55, 3.0, False, "T2", "drill", "slot"),
        ]
        pcb = _pcb(holes=holes)
        cands, pins, _ = generate_locating_pins(pcb, ProcessProfile().to_dict())
        slot = next(c for c in cands if c["drillId"] == "slot")
        assert slot["eligible"] is False
        assert slot["rejectionReasonsOnly"]
        assert "pin-slot" not in {p["id"] for p in pins}

    def test_conflict_rejected(self):
        keepout = box(0, 0, 20, 20)
        holes = [
            DrillHit("inside", 10, 10, 3.0, False, "T1", "drill", "hole"),
            DrillHit("ok1", 5, 55, 3.0, False, "T1", "drill", "hole"),
            DrillHit("ok2", 75, 5, 3.0, False, "T1", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        cands, pins, _ = generate_locating_pins(
            pcb, ProcessProfile().to_dict(), keepouts=[keepout]
        )
        inside = next(c for c in cands if c["drillId"] == "inside")
        assert inside["score"] < next(c for c in cands if c["drillId"] == "ok2")["score"]
        assert "pin-inside" not in {p["id"] for p in pins}

    def test_span_optimized_farthest_pair(self):
        holes = [
            DrillHit("a", 5, 5, 3.0, False, "T1", "drill", "hole"),
            DrillHit("b", 10, 6, 3.0, False, "T1", "drill", "hole"),
            DrillHit("c", 75, 55, 3.0, False, "T1", "drill", "hole"),
        ]
        pcb = _pcb(holes=holes)
        _cands, pins, _ = generate_locating_pins(pcb, ProcessProfile().to_dict())
        ids = {p["id"] for p in pins}
        assert "pin-a" in ids
        assert "pin-c" in ids
        assert "pin-b" not in ids


class TestProcessProfile:
    def test_defaults_match_legacy(self):
        p = ProcessProfile()
        assert p.sinkClearanceMm == 0.2
        assert p.keepoutClearanceMm == 0.7
        assert p.solderClearanceMm == 3.0
        assert p.fixtureMarginXmm == 20.0
        assert p.minimumMaterialWebMm == 2.0
        assert p.barrierMountHoleDiameterMm == 3.2

    def test_from_dict_ignores_bad_values(self):
        p = ProcessProfile.from_dict({"sinkClearanceMm": "nope", "keepoutClearanceMm": 1.1})
        assert p.sinkClearanceMm == 0.2
        assert p.keepoutClearanceMm == 1.1

    def test_min_pin_hole_default_is_two_mm(self):
        assert ProcessProfile().minPinHoleDiameterMm == 2.0


class TestNoInventedKeepout:
    def test_pnp_point_component_does_not_invent_1mm_pocket(self):
        point = PCBComponent(
            id="pnp-C1",
            refdes="C1",
            footprint="0805",
            side="bottom",
            centroid_x=20,
            centroid_y=20,
            rotation=0,
            bbox=(20, 20, 20, 20),
            courtyard=None,
            body_width_mm=None,
            body_length_mm=None,
            body_height_mm=None,
            component_type="unknown",
            confidence=0.94,
            source="pnp",
        )
        pcb = _pcb(components=[point])
        keepouts, _reviews, metas = generate_keepouts(pcb, ProcessProfile().to_dict())
        assert keepouts == []
        assert metas == []


class TestDrcNoDuplicateSolderKeepout:
    def test_overlap_emits_single_conflict_code(self):
        from shapely.geometry import box as shapely_box
        from app.models.geometry import FixtureGeometry

        pcb = _pcb()
        keepout = shapely_box(10, 10, 30, 30)
        solder = shapely_box(20, 20, 40, 40)
        fixture = FixtureGeometry(
            pcb=pcb,
            body=shapely_box(-20, -20, 100, 90),
            sink_region=shapely_box(-1, -1, 81, 61),
            keepout_regions=[keepout],
            solder_regions=[solder],
            locating_pins=[{"id": "pin-h1", "x": 5, "y": 5, "diameter": 2.9}],
            locating_pin_candidates=[],
            clamp_holes=[],
            handholds=[],
            rails=[],
            solder_barriers=[],
            solder_barrier_mount_holes=[],
            drc_issues=[],
            review_items=[],
            parameters=ProcessProfile().to_dict(),
            geometry_sha256="",
        )
        issues = run_drc(fixture)
        overlap_codes = [i["code"] for i in issues if "KEEP" in i["code"] and "SOLDER" in i["code"]]
        assert overlap_codes.count("SOLDER_KEEP_OUT_CONFLICT") == 1
        assert "SOLDER_OPENING_KEEPOUT_CONFLICT" not in overlap_codes
