import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_missing_required_settings_fail_fast(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("LLM_MODEL")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)