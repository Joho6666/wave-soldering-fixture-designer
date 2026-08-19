from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_solder_barrier_and_mounting_holes():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen = FixtureGenerator(analysis).generate({})
    
    assert len(gen["solder_barriers"]) == 2
    assert len(gen["solder_barrier_mount_holes"]) >= 2
    for h in gen["solder_barrier_mount_holes"]:
        assert h["diameter"] == 3.2
