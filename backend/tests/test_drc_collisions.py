from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator
from app.services.fixture.drc import run_drc

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"

def test_drc_collisions():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen = FixtureGenerator(analysis).generate({"minimumMaterialWebMm": 2.0})
    fixture_geom = gen["fixture_geometry"]
    issues = run_drc(fixture_geom)
    
    assert isinstance(issues, list)
    for issue in issues:
        assert "code" in issue
        assert "severity" in issue
