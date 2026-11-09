import os

# Fake values: tests must never use (or need) a real key.
# Real environment variables take priority over .env, so a real .env is ignored.
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["LLM_MODEL"] = "test-model"

import pytest
from fastapi.testclient import TestClient

from chatbot_backend.main import app
from chatbot_backend.store import store


@pytest.fixture(autouse=True)
def clean_store():
    store.reset()  # every test starts with an empty store
    yield
    store.reset()


@pytest.fixture
def client():
    return TestClient(app)