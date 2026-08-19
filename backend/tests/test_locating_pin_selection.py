from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_locating_pin_selection():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen = FixtureGenerator(analysis).generate({})
    assert len(gen["locating_candidates"]) == 31
    for c in gen["locating_candidates"]:
        assert "drillId" in c
        assert "score" in c
