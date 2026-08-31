"""BOM parser: height present vs missing, never invented."""
from app.services.bom.parser import explode_by_refdes, looks_like_bom_filename, parse_bom_bytes
from app.services.gerber.semantic_builder import build_semantic_model
from app.models.geometry import PCBGeometry
from shapely.geometry import box


def test_bom_with_component_height():
    csv = b"Designator,Value,Footprint,Description,Height\nC1,100nF,0805,decoupling,1.2\nU1,LM358,SOIC-8,opamp,1.75mm\n"
    rows = parse_bom_bytes(csv, "bom.csv")
    assert len(rows) == 2
    by_ref = explode_by_refdes(rows)
    assert by_ref["C1"].height_mm == 1.2
    assert by_ref["U1"].height_mm == 1.75
    assert by_ref["U1"].footprint == "SOIC-8"


def test_bom_missing_height_stays_none():
    csv = b"Ref,Value,Footprint\nR1,10k,0603\nC2,1uF,0805\n"
    rows = parse_bom_bytes(csv, "bom.csv")
    assert all(row.height_mm is None for row in rows)


def test_bom_height_blank_or_na():
    csv = b"Reference,Height\nD1,n/a\nD2,-\nD3,\n"
    rows = parse_bom_bytes(csv, "bom.csv")
    assert all(row.height_mm is None for row in rows)


def test_bom_explodes_multi_refdes():
    csv = b"Designator,Height\nC1 C2 C3,0.8\n"
    rows = parse_bom_bytes(csv, "bom.csv")
    by_ref = explode_by_refdes(rows)
    assert set(by_ref) == {"C1", "C2", "C3"}
    assert by_ref["C2"].height_mm == 0.8


def test_looks_like_bom_not_pnp():
    assert looks_like_bom_filename("project_bom.csv")
    assert not looks_like_bom_filename("pnp.csv")
    assert not looks_like_bom_filename("cpl.txt")


def test_bom_height_applied_to_semantic_component():
    from app.services.pnp.parser import parse_pnp_bytes

    pcb = PCBGeometry(
        outline=box(0, 0, 50, 40),
        holes=[],
        layers=[],
        source_sha256="t",
        geometry_sha256="t",
    )
    pnp = parse_pnp_bytes(b"Ref,X,Y,Layer\nC1,10,10,Bottom\n", "pnp.csv")
    bom = parse_bom_bytes(b"Designator,Height,Footprint\nC1,1.6,0805\n", "bom.csv")
    build_semantic_model(pcb, pnp_placements=pnp, bom_rows=bom)
    assert len(pcb.components) == 1
    assert pcb.components[0].body_height_mm == 1.6
    assert pcb.components[0].footprint == "0805"
