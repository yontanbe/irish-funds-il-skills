import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import load_data  # noqa: E402


@pytest.fixture(scope="session")
def data():
    return load_data()


@pytest.fixture(scope="session")
def root():
    return ROOT
