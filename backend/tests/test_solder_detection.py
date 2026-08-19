from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_solder_detection():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen = FixtureGenerator(analysis).generate({"solderClearanceMm": 3.0})
    assert len(gen["solder_windows"]) > 0
    for w in gen["solder_windows"]:
        assert w.area > 0
