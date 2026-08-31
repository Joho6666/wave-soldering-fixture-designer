"""PnP / CPL parser tests: mm, mil, top/bottom, Chinese and nonstandard headers."""
from app.services.pnp.parser import looks_like_pnp_filename, parse_pnp_bytes


def test_pnp_mm_standard_headers():
    csv = b"Designator,Mid X,Mid Y,Rotation,Layer,Package\nC1,10.0,20.0,90,Top,0805\nR2,15.5,8.0,0,Bottom,0603\n"
    rows = parse_pnp_bytes(csv, "pick_and_place.csv")
    assert len(rows) == 2
    by_ref = {r.refdes: r for r in rows}
    assert by_ref["C1"].x_mm == 10.0
    assert by_ref["C1"].y_mm == 20.0
    assert by_ref["C1"].side == "top"
    assert by_ref["C1"].footprint == "0805"
    assert by_ref["R2"].side == "bottom"


def test_pnp_mil_units():
    csv = b"Ref,X,Y,Rotation,Side,Unit\nU1,1000,2000,0,T,mil\n"
    rows = parse_pnp_bytes(csv, "centroid.csv")
    assert len(rows) == 1
    assert abs(rows[0].x_mm - 25.4) < 1e-6
    assert abs(rows[0].y_mm - 50.8) < 1e-6
    assert rows[0].side == "top"


def test_pnp_header_declares_mil():
    csv = b"Reference,X (mil),Y (mil),Rot,Layer\nJ1,393.7,196.85,180,B\n"
    rows = parse_pnp_bytes(csv, "pos.csv")
    assert len(rows) == 1
    assert abs(rows[0].x_mm - 10.0) < 0.02
    assert rows[0].side == "bottom"


def test_pnp_chinese_headers():
    csv = "位号,X,Y,角度,面,封装\nC10,1.2,3.4,0,底层,0402\n".encode("utf-8")
    rows = parse_pnp_bytes(csv, "贴片坐标.csv")
    assert len(rows) == 1
    assert rows[0].refdes == "C10"
    assert rows[0].side == "bottom"
    assert rows[0].footprint == "0402"


def test_pnp_nonstandard_column_names():
    csv = b"Part,PosX,PosY,Angle,TB,Pattern,Val\nQ1,4,5,45,B,SOT-23,MMBT3904\n"
    rows = parse_pnp_bytes(csv, "cpl.txt")
    assert len(rows) == 1
    assert rows[0].refdes == "Q1"
    assert rows[0].x_mm == 4.0
    assert rows[0].side == "bottom"
    assert rows[0].value == "MMBT3904"


def test_pnp_top_bottom_aliases():
    csv = b"Ref,X,Y,Layer\nA1,0,0,T\nA2,1,1,B\nA3,2,2,Front\nA4,3,3,Back\n"
    rows = parse_pnp_bytes(csv, "pnp.csv")
    sides = {r.refdes: r.side for r in rows}
    assert sides["A1"] == "top"
    assert sides["A2"] == "bottom"
    assert sides["A3"] == "top"
    assert sides["A4"] == "bottom"


def test_looks_like_pnp_filename():
    assert looks_like_pnp_filename("board-pnp.csv")
    assert looks_like_pnp_filename("CPL.txt")
    assert looks_like_pnp_filename("pick-and-place.csv")
    assert looks_like_pnp_filename("pos.csv")
    assert not looks_like_pnp_filename("bom.csv")
    assert not looks_like_pnp_filename("outline.gko")
    assert not looks_like_pnp_filename("board.txt")
