import json
import sys
import types
from pathlib import Path

import pytest

# redis_config connects to the cluster when imported, which is what we want in a
# deployment but makes controller.py unimportable here. Stub it before any test
# module imports the controller.
sys.modules["redis_config"] = types.SimpleNamespace(redis_instance=None)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def google_verdict():
    """A fresh copy of the sample Play Integrity verdict for each test."""
    return load_fixture("sample_google_verdict.json")
