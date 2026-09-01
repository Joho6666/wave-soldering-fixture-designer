from shapely.geometry import box

from app.services.fixture.solder_optimizer import apply_directional_opening, wave_leading_trailing
from app.geometry.transform import Transform2D


def _params(direction: str, **extra):
    base = {
        "directionalOpeningEnabled": True,
        "waveDirection": direction,
        "solderLeadingExtensionMm": 1.0,
        "solderTrailingExtensionMm": 3.0,
        "solderSideClearanceMm": 0.0,
        "solderEntryChamferMm": 0.0,
        "solderExitChamferMm": 0.0,
    }
    base.update(extra)
    return base


def test_plus_x_and_minus_x_are_mirrors():
    window = box(10, 10, 20, 16)
    plus = apply_directional_opening(window, _params("+X"))
    minus = apply_directional_opening(window, _params("-X"))
    assert plus.bounds[2] - window.bounds[2] > minus.bounds[2] - window.bounds[2]
    assert window.bounds[0] - minus.bounds[0] > window.bounds[0] - plus.bounds[0]
    width_plus = plus.bounds[2] - plus.bounds[0]
    width_minus = minus.bounds[2] - minus.bounds[0]
    assert abs(width_plus - width_minus) < 1e-6


def test_plus_y_and_minus_y_are_mirrors():
    window = box(10, 10, 16, 20)
    plus = apply_directional_opening(window, _params("+Y"))
    minus = apply_directional_opening(window, _params("-Y"))
    height_plus = plus.bounds[3] - plus.bounds[1]
    height_minus = minus.bounds[3] - minus.bounds[1]
    assert abs(height_plus - height_minus) < 1e-6
    assert plus.bounds[3] > window.bounds[3]
    assert minus.bounds[1] < window.bounds[1]


def test_disabled_directional_opening_is_noop():
    window = box(10, 10, 20, 16)
    out = apply_directional_opening(window, {"directionalOpeningEnabled": False, "waveDirection": "+X", "solderTrailingExtensionMm": 5})
    assert abs(out.area - window.area) < 1e-9


def test_rotated_pcb_opening_matches_axis_remap():
    window = box(0, 0, 8, 4)
    plus_x = apply_directional_opening(window, _params("+X"))
    rotated_window = Transform2D(rotation_deg=90).apply(window)
    plus_y = apply_directional_opening(rotated_window, _params("+Y"))
    expected = Transform2D(rotation_deg=90).apply(plus_x)
    assert abs(plus_y.bounds[0] - expected.bounds[0]) < 0.2
    assert abs(plus_y.bounds[1] - expected.bounds[1]) < 0.2
    assert abs((plus_y.bounds[2] - plus_y.bounds[0]) - (expected.bounds[2] - expected.bounds[0])) < 0.3


def test_leading_trailing_mapping():
    assert wave_leading_trailing("+X") == ("-X", "+X")
    assert wave_leading_trailing("-X") == ("+X", "-X")
    assert wave_leading_trailing("+Y") == ("-Y", "+Y")
    assert wave_leading_trailing("-Y") == ("+Y", "-Y")
