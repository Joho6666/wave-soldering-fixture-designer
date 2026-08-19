from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_corner_relief():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen1 = FixtureGenerator(analysis).generate({"filletRadiusMm": 1.85, "sinkClearanceMm": 0.2})
    gen2 = FixtureGenerator(analysis).generate({"filletRadiusMm": 3.0, "sinkClearanceMm": 0.2})
    
    assert gen1["sink_area"].area > 0
    assert gen2["sink_area"].area > gen1["sink_area"].area
