from tests.test_auth import auth_header, signup


def signup_token(client, name, email):
    return signup(client, name, email).get_json()["access_token"]


def make_request(client):
    ada = signup_token(client, "Ada", "ada@example.com")
    grace = signup_token(client, "Grace", "grace@example.com")
    response = client.post("/friends/add", json={"email": "grace@example.com"}, headers=auth_header(ada))
    return ada, grace, response


def test_add_friend_request_and_prevent_duplicates(client):
    ada, _, response = make_request(client)
    assert response.status_code == 201
    assert response.get_json()["friend_request"]["status"] == "pending"
    assert client.post("/friends/add", json={"email": "grace@example.com"}, headers=auth_header(ada)).status_code == 409


def test_add_friend_rejects_unauthorized_unknown_and_self(client):
    assert client.post("/friends/add", json={"email": "grace@example.com"}).status_code == 401
    ada = signup_token(client, "Ada", "ada@example.com")
    assert client.post("/friends/add", json={"email": "missing@example.com"}, headers=auth_header(ada)).status_code == 404
    assert client.post("/friends/add", json={"email": "ada@example.com"}, headers=auth_header(ada)).status_code == 400


def test_accept_list_and_remove_friend(client):
    ada, grace, request_response = make_request(client)
    request_id = request_response.get_json()["friend_request"]["id"]
    accepted = client.post(f"/friends/accept/{request_id}", headers=auth_header(grace))
    assert accepted.status_code == 200
    friends = client.get("/friends", headers=auth_header(ada))
    assert friends.status_code == 200
    assert friends.get_json()["friends"][0]["email"] == "grace@example.com"
    grace_id = friends.get_json()["friends"][0]["id"]
    assert client.delete(f"/friends/{grace_id}", headers=auth_header(ada)).status_code == 204
    assert client.get("/friends", headers=auth_header(ada)).get_json()["friends"] == []


def test_accept_requires_recipient_and_pending_request(client):
    ada, grace, request_response = make_request(client)
    request_id = request_response.get_json()["friend_request"]["id"]
    assert client.post(f"/friends/accept/{request_id}", headers=auth_header(ada)).status_code == 403
    assert client.post("/friends/accept/999", headers=auth_header(grace)).status_code == 404
    assert client.post(f"/friends/accept/{request_id}", headers=auth_header(grace)).status_code == 200
    assert client.post(f"/friends/accept/{request_id}", headers=auth_header(grace)).status_code == 409


def test_friends_routes_require_auth_and_remove_missing_friend_fails(client):
    assert client.get("/friends").status_code == 401
    assert client.delete("/friends/1").status_code == 401
    ada = signup_token(client, "Ada", "ada@example.com")
    assert client.delete("/friends/44", headers=auth_header(ada)).status_code == 404
