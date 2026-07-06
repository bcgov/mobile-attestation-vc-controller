import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def google_verdict():
    """A fresh copy of the sample Play Integrity verdict for each test."""
    return load_fixture("sample_google_verdict.json")
