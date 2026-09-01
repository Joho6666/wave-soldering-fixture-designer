from shapely.geometry import box

from app.geometry.transform import Transform2D
from app.models.geometry import PCBGeometry, DrillHit
from app.models.panel import PCBInstance
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.manifest import build_fixture_manifest
from app.services.panel.grid import build_grid_panel
from app.services.rules.process_profile import ProcessProfile, parameter_catalog


def _pcb():
    return PCBGeometry(
        outline=box(0, 0, 40, 30),
        holes=[
            DrillHit("h1", 4, 4, 3.0, False, "T1", "drill"),
            DrillHit("h2", 36, 26, 3.0, False, "T1", "drill"),
        ],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )


def test_transform_rotation_cardinal():
    t = Transform2D(rotation_deg=90)
    x, y = t.apply_xy(10, 0)
    assert abs(x - 0) < 1e-9
    assert abs(y - 10) < 1e-9
    lx, ly = t.global_to_local(x, y)
    assert abs(lx - 10) < 1e-9
    assert abs(ly - 0) < 1e-9
    for deg in (0, 90, 180, 270):
        tf = Transform2D(tx=5, ty=7, rotation_deg=deg)
        gx, gy = tf.apply_xy(3, 4)
        bx, by = tf.global_to_local(gx, gy)
        assert abs(bx - 3) < 1e-9
        assert abs(by - 4) < 1e-9


def test_transform_mirror_and_translation():
    t = Transform2D(tx=10, ty=2, mirror_x=True)
    x, y = t.apply_xy(3, 4)
    assert abs(x - 7) < 1e-9
    assert abs(y - 6) < 1e-9
    geom = t.apply(box(0, 0, 2, 1))
    assert geom.bounds[2] <= 10 + 1e-9


def test_grid_panel_2x2_keeps_instance_frames():
    panel = build_grid_panel(_pcb(), {"panelEnabled": True, "panelRows": 2, "panelCols": 2, "panelBoardSpacingMm": 2, "panelOuterMarginMm": 5})
    assert panel is not None
    assert len(panel.pcb_instances) == 4
    assert panel.rows == 2 and panel.cols == 2
    ids = {i.id for i in panel.pcb_instances}
    assert "pcb-1-1" in ids and "pcb-2-2" in ids
    assert len(panel.v_cuts) >= 2
    assert len(panel.tooling_holes) == 4
    a = panel.pcb_instances[0].global_outline()
    b = panel.pcb_instances[-1].global_outline()
    assert a.centroid.distance(b.centroid) > 20


def test_panel_multi_instance_fixture_generation():
    gen = FixtureGenerator({"pcb_geometry": _pcb()})
    result = gen.generate({"panelEnabled": True, "panelRows": 2, "panelCols": 2, "panelBoardSpacingMm": 3})
    assert result["featureSummary"]["panelInstanceCount"] == 4
    assert result["panel"]["instanceCount"] == 4
    assert len(result["pins"]) >= 2


def test_manifest_contains_trace_fields():
    gen = FixtureGenerator({"pcb_geometry": _pcb()})
    result = gen.generate({})
    manifest = build_fixture_manifest(job_id="job-test", fixture_data=result, parameters=result["fixture_geometry"].parameters)
    assert manifest["softwareVersion"]
    assert manifest["algorithmVersion"]
    assert manifest["rulesVersion"]
    assert manifest["geometrySha256"] == result["geometrySha256"]
    assert "generatedFeatures" in manifest
    assert "drcResults" in manifest


def test_process_profile_catalog_has_categories():
    catalog = parameter_catalog()
    names = {p["name"] for p in catalog["parameters"]}
    assert "directionalOpeningEnabled" in names
    assert "pressureReliefEnabled" in names
    assert "panelEnabled" in names
    assert ProcessProfile().directionalOpeningEnabled is False
    assert ProcessProfile().pressureReliefEnabled is False


def test_pcb_instance_transform_roundtrip():
    pcb = _pcb()
    inst = PCBInstance(id="i1", source_pcb=pcb, x=15, y=8, rotation=180, mirror=False)
    g = inst.global_outline()
    back = inst.transform.inverse().apply(g)
    assert abs(back.centroid.x - pcb.outline.centroid.x) < 1e-6
    assert abs(back.centroid.y - pcb.outline.centroid.y) < 1e-6
