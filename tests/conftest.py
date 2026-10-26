import pytest

from app import database
from app.config import settings


@pytest.fixture(autouse=True)
def isolated_demo_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "audit.db")
    monkeypatch.setattr(settings, "approval_api_key", "test-reviewer-token")
