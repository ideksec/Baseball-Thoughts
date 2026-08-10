"""Shared test fixtures for baseball_lab."""

import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_json_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def gumbo_feed() -> dict:
    return load_json_fixture("gumbo_feed_trimmed.json")


@pytest.fixture
def wp_entries() -> list[dict]:
    return load_json_fixture("win_probability.json")


@pytest.fixture
def schedule_gameday() -> dict:
    return load_json_fixture("statsapi_schedule_gameday.json")


@pytest.fixture
def schedule_doubleheader() -> dict:
    return load_json_fixture("statsapi_schedule_doubleheader.json")


@pytest.fixture
def schedule_empty() -> dict:
    return load_json_fixture("statsapi_schedule_empty.json")


@pytest.fixture
def statcast_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "statcast_game.csv")


@pytest.fixture
def gamelog_df() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "gamelog_sample.csv")
