import os

# Fake values: tests must never need (or use) a real key.
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["LLM_MODEL"] = "test-model"
os.environ["LLM_MAX_INPUT_CHARS"] = "4000"
os.environ["LLM_MAX_OUTPUT_TOKENS"] = "512"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.message_store import store


@pytest.fixture(autouse=True)
def clean_state():
    store.reset()
    yield
    store.reset()
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)