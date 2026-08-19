from shapely.geometry import Polygon, box
from app.models.geometry import FixtureGeometry, PCBGeometry
from app.services.fixture.generator import FixtureGenerator


def _make_fixture(pins, keepouts):
    pcb = PCBGeometry(
        outline=Polygon([(0, 0), (100, 0), (100, 80), (0, 80)]),
        holes=[],
        layers=[],
        source_sha256="src",
        geometry_sha256="geom",
    )
    return FixtureGeometry(
        pcb=pcb,
        body=box(-10, -10, 110, 90),
        sink_region=box(-0.2, -0.2, 100.2, 80.2),
        keepout_regions=keepouts,
        solder_regions=[box(20, 20, 40, 40)],
        locating_pins=pins,
        locating_pin_candidates=[],
        clamp_holes=[{"id": "c1", "x": 10, "y": 90, "diameter": 3.4}],
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={},
        geometry_sha256="",
        spring_clip_holes=[{"id": "s1", "x": 50, "y": 40, "diameter": 4.9}],
    )


def test_digest_deterministic_under_element_reordering():
    # 顺序列出 pins 和 keepouts
    pins_1 = [{"id": "p1", "x": 5.0, "y": 5.0, "diameter": 3.0}, {"id": "p2", "x": 95.0, "y": 75.0, "diameter": 3.0}]
    keepouts_1 = [box(10, 10, 20, 20), box(60, 60, 80, 80)]
    f1 = _make_fixture(pins_1, keepouts_1)
    gen = FixtureGenerator({"pcb_geometry": f1.pcb})
    digest_1 = gen._geometry_digest(f1)

    # 逆序列出 pins 和 keepouts
    pins_2 = [{"id": "p2", "x": 95.0, "y": 75.0, "diameter": 3.0}, {"id": "p1", "x": 5.0, "y": 5.0, "diameter": 3.0}]
    keepouts_2 = [box(60, 60, 80, 80), box(10, 10, 20, 20)]
    f2 = _make_fixture(pins_2, keepouts_2)
    digest_2 = gen._geometry_digest(f2)

    assert digest_1 == digest_2
    assert len(digest_1) == 64
