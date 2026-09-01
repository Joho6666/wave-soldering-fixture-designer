import ezdxf
from shapely.geometry import box

from app.models.geometry import DrillHit, PCBGeometry
from app.services.exporters.dxf_exporter import export_fixture_dxf
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.manifest import build_fixture_manifest


def _pcb():
    return PCBGeometry(
        outline=box(0, 0, 80, 60),
        holes=[
            DrillHit("h1", 5, 5, 3.0, False, "T1", "drill"),
            DrillHit("h2", 75, 55, 3.0, False, "T1", "drill"),
            DrillHit("h3", 20, 20, 1.0, True, "T2", "drill"),
        ],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )


def _strip_manifest(manifest: dict) -> dict:
    copy = dict(manifest)
    copy.pop("createdAt", None)
    return copy


def _dxf_geometry_fingerprint(path) -> tuple:
    doc = ezdxf.readfile(str(path))
    rows = []
    for e in doc.modelspace():
        dxftype = e.dxftype()
        layer = e.dxf.layer
        if dxftype == "CIRCLE":
            rows.append((dxftype, layer, round(e.dxf.center.x, 6), round(e.dxf.center.y, 6), round(e.dxf.radius, 6)))
        elif dxftype == "LWPOLYLINE":
            pts = tuple((round(p[0], 6), round(p[1], 6)) for p in e.get_points("xy"))
            rows.append((dxftype, layer, pts))
        elif dxftype == "LINE":
            rows.append((dxftype, layer, round(e.dxf.start.x, 6), round(e.dxf.start.y, 6), round(e.dxf.end.x, 6), round(e.dxf.end.y, 6)))
        else:
            rows.append((dxftype, layer))
    return tuple(sorted(rows))


def test_deterministic_generation_twenty_runs(tmp_path):
    pcb = _pcb()
    hashes = []
    manifests = []
    fingerprints = []
    for i in range(20):
        result = FixtureGenerator({"pcb_geometry": pcb}).generate({})
        hashes.append(result["geometrySha256"])
        dxf_path = tmp_path / f"run_{i}.dxf"
        export_fixture_dxf(result, str(dxf_path))
        fingerprints.append(_dxf_geometry_fingerprint(dxf_path))
        manifests.append(_strip_manifest(build_fixture_manifest(
            job_id="det",
            fixture_data=result,
            parameters=result["fixture_geometry"].parameters,
        )))
    assert len(set(hashes)) == 1
    assert len({row["geometrySha256"] for row in manifests}) == 1
    assert len(set(fingerprints)) == 1
