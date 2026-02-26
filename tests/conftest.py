import json
from pathlib import Path

import pytest

from policy_localiser.engine.models import SchoolRecord

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def template_path():
    return FIXTURES_DIR / "templates" / "Sample_Policy.docx"


@pytest.fixture
def logos_dir():
    return FIXTURES_DIR / "logos"


@pytest.fixture
def sample_schools():
    with open(FIXTURES_DIR / "sample_schools.json") as f:
        data = json.load(f)
    return [SchoolRecord(**s) for s in data]


@pytest.fixture
def stm_school(sample_schools):
    return next(s for s in sample_schools if s.SchoolCode == "STM")
