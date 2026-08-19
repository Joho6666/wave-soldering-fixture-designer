from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_geometry_consistency():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen1 = FixtureGenerator(analysis).generate({"sinkClearanceMm": 0.2})
    gen2 = FixtureGenerator(analysis).generate({"sinkClearanceMm": 0.2})
    
    assert gen1["geometrySha256"] == gen2["geometrySha256"]
    assert gen1["fixtureWidth"] == gen2["fixtureWidth"]
    assert gen1["fixtureHeight"] == gen2["fixtureHeight"]
