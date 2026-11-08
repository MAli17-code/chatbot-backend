import pytest

URL = "/api/v1/messages"


def make(client, role="user", content="hello"):
    response = client.post(URL, json={"role": role, "content": content})
    assert response.status_code == 201
    return response.json()


def test_create_valid_message(client):
    response = client.post(URL, json={"role": "user", "content": "What is FastAPI?"})
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["role"] == "user"
    assert body["content"] == "What is FastAPI?"
    assert body["created_at"]


def test_content_is_trimmed(client):
    assert make(client, content="  hi  ")["content"] == "hi"


@pytest.mark.parametrize("content", ["", "   "])
def test_reject_empty_message(client, content):
    response = client.post(URL, json={"role": "user", "content": content})
    assert response.status_code == 422


def test_reject_oversized_content(client):
    response = client.post(URL, json={"role": "user", "content": "x" * 2001})
    assert response.status_code == 422


def test_reject_invalid_role(client):
    response = client.post(URL, json={"role": "admin", "content": "hi"})
    assert response.status_code == 422


def test_list_with_limit_offset_and_role(client):
    for i in range(5):
        make(client, "user", f"user {i}")
    for i in range(3):
        make(client, "assistant", f"assistant {i}")

    page = client.get(URL, params={"limit": 2, "offset": 1}).json()
    assert [m["content"] for m in page] == ["user 1", "user 2"]

    assistants = client.get(URL, params={"role": "assistant"}).json()
    assert len(assistants) == 3
    assert all(m["role"] == "assistant" for m in assistants)

    combined = client.get(URL, params={"role": "user", "limit": 2, "offset": 4}).json()
    assert [m["content"] for m in combined] == ["user 4"]


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"role": "admin"}],
)
def test_list_rejects_invalid_query_params(client, params):
    assert client.get(URL, params=params).status_code == 422


def test_retrieve_existing_message(client):
    created = make(client, content="find me")
    response = client.get(f"{URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_missing_message_returns_custom_404(client):
    response = client.get(f"{URL}/999")
    assert response.status_code == 404
    assert response.json()["error"] == "message_not_found"


def test_update_message(client):
    created = make(client, content="old")
    response = client.patch(f"{URL}/{created['id']}", json={"content": "new"})
    assert response.status_code == 200
    assert response.json()["content"] == "new"
    assert client.get(f"{URL}/{created['id']}").json()["content"] == "new"


def test_update_rejects_empty_content(client):
    created = make(client)
    response = client.patch(f"{URL}/{created['id']}", json={"content": "  "})
    assert response.status_code == 422


def test_update_and_delete_unknown_id_return_404(client):
    assert client.patch(f"{URL}/999", json={"content": "x"}).status_code == 404
    assert client.delete(f"{URL}/999").status_code == 404


def test_delete_message(client):
    created = make(client)
    response = client.delete(f"{URL}/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"{URL}/{created['id']}").status_code == 404