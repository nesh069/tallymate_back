def signup(client, name="Ada", email="ada@example.com", password="password123"):
    return client.post("/auth/signup", json={"name": name, "email": email, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_creates_user_and_returns_access_token(client):
    response = signup(client)
    assert response.status_code == 201
    data = response.get_json()
    assert data["user"]["email"] == "ada@example.com"
    assert data["access_token"]
    assert "password_hash" not in data["user"]


def test_signup_rejects_duplicate_and_invalid_payload(client):
    signup(client)
    assert signup(client).status_code == 409
    assert client.post("/auth/signup", json={"name": "Ada", "email": "a@b.com", "password": "short"}).status_code == 400


def test_login_returns_access_and_refresh_tokens(client):
    signup(client)
    response = client.post("/auth/login", json={"email": "ADA@example.com", "password": "password123"})
    assert response.status_code == 200
    assert response.get_json()["access_token"]
    assert response.get_json()["refresh_token"]


def test_login_rejects_bad_credentials(client):
    signup(client)
    assert client.post("/auth/login", json={"email": "ada@example.com", "password": "wrongpass"}).status_code == 401
    assert client.post("/auth/login", json={"email": "missing@example.com", "password": "password123"}).status_code == 401


def test_me_requires_token_and_returns_user(client):
    assert client.get("/auth/me").status_code == 401
    token = signup(client).get_json()["access_token"]
    response = client.get("/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()["user"]["name"] == "Ada"


def test_signup_defaults_currency_to_usd(client):
    data = signup(client).get_json()
    assert data["user"]["currency"] == "USD"


def test_update_currency(client):
    token = signup(client).get_json()["access_token"]
    response = client.patch("/auth/me", json={"currency": "KSH"}, headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()["user"]["currency"] == "KSH"
    assert client.get("/auth/me", headers=auth_header(token)).get_json()["user"]["currency"] == "KSH"


def test_update_currency_rejects_invalid_values(client):
    token = signup(client).get_json()["access_token"]
    assert client.patch("/auth/me", json={"currency": "EUR"}, headers=auth_header(token)).status_code == 400
    assert client.patch("/auth/me", json={"currency": "ksh"}, headers=auth_header(token)).status_code == 200


def test_update_me_requires_token(client):
    assert client.patch("/auth/me", json={"currency": "KSH"}).status_code == 401
