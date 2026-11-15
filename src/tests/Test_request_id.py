import uuid

import pytest


def test_valid_request_id_is_returned(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_missing_request_id_is_generated(client):
    value = client.get("/health").headers["X-Request-ID"]
    uuid.UUID(value)   # raises if it isn't a valid UUID


@pytest.mark.parametrize("bad", ["x" * 65, "has space", "semi;colon", "<script>"])
def test_unsafe_request_id_is_replaced(client, bad):
    value = client.get("/health", headers={"X-Request-ID": bad}).headers["X-Request-ID"]
    assert value != bad
    uuid.UUID(value)


def test_error_body_has_matching_request_id(client):
    response = client.get("/api/v1/messages/999", headers={"X-Request-ID": "trace-42"})
    assert response.status_code == 404
    assert response.json()["error"]["request_id"] == "trace-42"
    assert response.headers["X-Request-ID"] == "trace-42"


def test_validation_error_still_gets_header(client):
    response = client.post("/api/v1/messages", json={"role": "admin", "content": ""})
    assert response.status_code == 422
    assert response.headers["X-Request-ID"]