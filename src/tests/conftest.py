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