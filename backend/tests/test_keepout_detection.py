from pathlib import Path
from app.services.gerber.parser import GerberParser
from app.services.fixture.generator import FixtureGenerator

FIXTURE_ARCHIVE = Path(__file__).parent / "fixtures" / "wave_fixture_outline_drill.zip"
PARAMETERS = {"keepoutClearanceMm": 0.8}

def test_keepout_detection():
    analysis = GerberParser().parse_zip(str(FIXTURE_ARCHIVE))
    gen = FixtureGenerator(analysis).generate(PARAMETERS)
    # 无 GBO/GBS 情况下生成 Review 项提示工程师，而不伪造固定几何
    assert "keepout_zones" in gen
    assert isinstance(gen["keepout_zones"], list)
