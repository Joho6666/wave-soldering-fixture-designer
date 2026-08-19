from unittest.mock import MagicMock
from gerbonara.graphic_primitives import Line as PrimitiveLine, Arc as PrimitiveArc, Circle
from app.services.gerber.parser import GerberParser


def test_gerber_geometry_with_primitive_arc_and_none_aperture():
    parser = GerberParser()
    mock_gerber = MagicMock()

    # 构造含 PrimitiveLine, PrimitiveArc, Circle 的图元列表
    p_line = PrimitiveLine(0.0, 0.0, 10.0, 0.0, width=0.2)
    p_arc = PrimitiveArc(10.0, 0.0, 10.0, 10.0, 10.0, 5.0, clockwise=True, width=0.2)
    p_circle = Circle(50.0, 50.0, r=1.0)

    mock_gerber.primitives.return_value = [p_line, p_arc, p_circle]

    geom = parser._gerber_geometry(mock_gerber)
    assert not geom.is_empty
    assert geom.is_valid
