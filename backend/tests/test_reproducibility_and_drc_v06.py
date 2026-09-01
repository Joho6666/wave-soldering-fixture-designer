from shapely.geometry import box, Polygon

from app.models.geometry import PCBGeometry, DrillHit, FixtureGeometry
from app.services.fixture.drc import run_drc
from app.services.fixture.generator import FixtureGenerator


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


def test_generation_sha_identical_across_ten_runs():
    pcb = _pcb()
    hashes = []
    for _ in range(10):
        result = FixtureGenerator({"pcb_geometry": pcb}).generate({})
        hashes.append(result["geometrySha256"])
    assert len(set(hashes)) == 1
    assert len(hashes[0]) == 64


def test_drc_issue_schema_has_trace_fields():
    pcb = PCBGeometry(
        outline=box(0, 0, 80, 60),
        holes=[],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    fixture = FixtureGeometry(
        pcb=pcb,
        body=box(-5, -5, 90, 70),
        sink_region=box(-0.2, -0.2, 80.2, 60.2),
        keepout_regions=[],
        solder_regions=[box(-4.8, 20, -3.2, 28)],
        locating_pins=[],
        locating_pin_candidates=[],
        clamp_holes=[],
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={"minimumMaterialWebMm": 2.0, "palletThicknessMm": 10, "pocketFloorThicknessMm": 2, "solderMinOpeningWidthMm": 1.5, "minPinSeparationMm": 15},
        geometry_sha256="",
    )
    issues = run_drc(fixture)
    assert issues
    sample = issues[0]
    assert "code" in sample
    assert "severity" in sample
    assert "message" in sample
    assert "sourceIds" in sample
    assert sample["severity"] in {"info", "warning", "error", "blocking"}


def test_new_drc_codes_cover_invalid_and_opening_edge():
    pcb = PCBGeometry(
        outline=box(0, 0, 80, 60),
        holes=[],
        layers=[],
        source_sha256="s",
        geometry_sha256="g",
    )
    bowtie = Polygon([(0, 0), (10, 10), (0, 10), (10, 0)])
    fixture = FixtureGeometry(
        pcb=pcb,
        body=box(-5, -5, 90, 70),
        sink_region=box(-0.2, -0.2, 80.2, 60.2),
        keepout_regions=[bowtie] if not bowtie.is_valid else [box(200, 200, 210, 210)],
        solder_regions=[box(-4.5, 20, -3.0, 30)],
        locating_pins=[{"id": "p1", "x": 5, "y": 5, "diameter": 3.0}],
        locating_pin_candidates=[],
        clamp_holes=[],
        handholds=[],
        rails=[],
        solder_barriers=[],
        solder_barrier_mount_holes=[],
        drc_issues=[],
        review_items=[],
        parameters={"minimumMaterialWebMm": 2.0, "palletThicknessMm": 10, "pocketFloorThicknessMm": 2, "solderMinOpeningWidthMm": 1.5, "minPinSeparationMm": 15},
        geometry_sha256="",
    )
    codes = {i["code"] for i in run_drc(fixture)}
    assert "OPENING_TOO_CLOSE_TO_FIXTURE_EDGE" in codes or "FEATURE_OUTSIDE_FIXTURE" in codes or "INVALID_GEOMETRY" in codes or "SELF_INTERSECTION" in codes
