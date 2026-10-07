import pytest

from node_verdict.scenario import build_scenario


@pytest.fixture(scope="session")
def scenario():
    return build_scenario()
