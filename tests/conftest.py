import pytest

from campaign_copilot.data.generate import build


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    """One synthetic database for the whole test session."""
    return build(tmp_path_factory.mktemp("data") / "northwind.db")
