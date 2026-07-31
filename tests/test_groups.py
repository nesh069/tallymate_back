def signup(client, name="Ada", email="ada@example.com", password="password123"):
    return client.post("/auth/signup", json={"name": name, "email": email, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def get_token(client):
    return signup(client).get_json()["access_token"]


def create_group(client, token, name="Trip to Paris"):
    return client.post("/groups", json={"name": name}, headers=auth_header(token))


# Create Group 

def test_create_group_requires_auth(client):
    response = client.post("/groups", json={"name": "Test"})
    assert response.status_code == 401


def test_create_group_success(client):
    token = get_token(client)
    response = create_group(client, token)
    assert response.status_code == 201
    data = response.get_json()
    assert data["group"]["name"] == "Trip to Paris"
    assert data["group"]["created_by"] == 1
    assert len(data["group"]["members"]) == 1
    assert data["group"]["members"][0]["name"] == "Ada"


def test_create_group_missing_name(client):
    token = get_token(client)
    response = client.post("/groups", json={}, headers=auth_header(token))
    assert response.status_code == 400


def test_create_group_invalid_body(client):
    token = get_token(client)
    response = client.post("/groups", json="not an object", headers=auth_header(token))
    assert response.status_code == 400


# List Groups 

def test_list_groups_requires_auth(client):
    response = client.get("/groups")
    assert response.status_code == 401


def test_list_groups_empty(client):
    token = get_token(client)
    response = client.get("/groups", headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()["groups"] == []


def test_list_groups_returns_owned_groups(client):
    token = get_token(client)
    create_group(client, token, "Work")
    create_group(client, token, "Home")
    response = client.get("/groups", headers=auth_header(token))
    assert response.status_code == 200
    assert len(response.get_json()["groups"]) == 2


def test_list_groups_only_shows_membership_groups(client):
    token1 = get_token(client)
    create_group(client, token1, "Ada's Group")

    # Sign up a second user
    token2 = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    create_group(client, token2, "Bob's Group")

    # Ada should only see her own group
    response = client.get("/groups", headers=auth_header(token1))
    groups = response.get_json()["groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "Ada's Group"


# Get Group Detail 

def test_get_group_requires_auth(client):
    response = client.get("/groups/1")
    assert response.status_code == 401


def test_get_group_not_found(client):
    token = get_token(client)
    response = client.get("/groups/999", headers=auth_header(token))
    assert response.status_code == 404


def test_get_group_non_member_forbidden(client):
    token1 = get_token(client)
    group = create_group(client, token1).get_json()["group"]

    token2 = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    response = client.get(f"/groups/{group['id']}", headers=auth_header(token2))
    assert response.status_code == 403


def test_get_group_success(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]
    response = client.get(f"/groups/{group['id']}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()["group"]["name"] == "Trip to Paris"


# Add Member 

def test_add_member_requires_auth(client):
    response = client.post("/groups/1/members", json={"user_id": 2})
    assert response.status_code == 401


def test_add_member_only_owner_can_add(client):
    token_owner = get_token(client)
    group = create_group(client, token_owner).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    token_charlie = signup(client, name="Charlie", email="charlie@example.com").get_json()["access_token"]

    # Bob is not the owner, should be forbidden
    response = client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": 3},
        headers=auth_header(token_bob),
    )
    assert response.status_code == 403


def test_add_member_success(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    # Get Bob's user ID from /auth/me
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]

    response = client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": bob["id"]},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    member_ids = [m["id"] for m in response.get_json()["group"]["members"]]
    assert bob["id"] in member_ids


def test_add_member_already_in_group(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    response = client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": 1},
        headers=auth_header(token),
    )
    assert response.status_code == 409


def test_add_member_invalid_user_id(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    response = client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": 999},
        headers=auth_header(token),
    )
    assert response.status_code == 404


def test_add_member_missing_user_id(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    response = client.post(
        f"/groups/{group['id']}/members",
        json={},
        headers=auth_header(token),
    )
    assert response.status_code == 400


# Remove Member 

def test_remove_member_requires_auth(client):
    response = client.delete("/groups/1/members/2")
    assert response.status_code == 401


def test_remove_member_only_owner_can_remove(client):
    token_owner = get_token(client)
    group = create_group(client, token_owner).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]

    # Add Bob to the group
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]
    client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": bob["id"]},
        headers=auth_header(token_owner),
    )

    # Charlie signs up and tries to remove Bob (not the owner)
    token_charlie = signup(client, name="Charlie", email="charlie@example.com").get_json()["access_token"]
    response = client.delete(
        f"/groups/{group['id']}/members/{bob['id']}",
        headers=auth_header(token_charlie),
    )
    assert response.status_code == 403


def test_remove_member_cannot_remove_self(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    response = client.delete(
        f"/groups/{group['id']}/members/1",
        headers=auth_header(token),
    )
    assert response.status_code == 400


def test_remove_member_success(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]

    # Add Bob first
    client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": bob["id"]},
        headers=auth_header(token),
    )

    # Remove Bob
    response = client.delete(
        f"/groups/{group['id']}/members/{bob['id']}",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    member_ids = [m["id"] for m in response.get_json()["group"]["members"]]
    assert bob["id"] not in member_ids


def test_remove_member_not_in_group(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]

    response = client.delete(
        f"/groups/{group['id']}/members/{bob['id']}",
        headers=auth_header(token),
    )
    assert response.status_code == 404

# Delete Group
 
def test_delete_group_requires_auth(client):
    response = client.delete("/groups/1")
    assert response.status_code == 401


def test_delete_group_only_owner_can_delete(client):
    token_owner = get_token(client)
    group = create_group(client, token_owner).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]
    client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": bob["id"]},
        headers=auth_header(token_owner),
    )

    response = client.delete(f"/groups/{group['id']}", headers=auth_header(token_bob))
    assert response.status_code == 403


def test_delete_group_success(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    response = client.delete(f"/groups/{group['id']}", headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()["message"] == "Group deleted."

    # Verify it's gone
    response = client.get(f"/groups/{group['id']}", headers=auth_header(token))
    assert response.status_code == 404


def test_delete_group_not_found(client):
    token = get_token(client)
    response = client.delete("/groups/999", headers=auth_header(token))
    assert response.status_code == 404


# Leave Group
 
def test_leave_group_requires_auth(client):
    response = client.delete("/groups/1/leave")
    assert response.status_code == 401


def test_leave_group_owner_cannot_leave(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    response = client.delete(f"/groups/{group['id']}/leave", headers=auth_header(token))
    assert response.status_code == 400


def test_leave_group_success(client):
    token_owner = get_token(client)
    group = create_group(client, token_owner).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]
    client.post(
        f"/groups/{group['id']}/members",
        json={"user_id": bob["id"]},
        headers=auth_header(token_owner),
    )

    response = client.delete(f"/groups/{group['id']}/leave", headers=auth_header(token_bob))
    assert response.status_code == 200
    assert response.get_json()["message"] == "You have left the group."

    # Verify Bob is no longer in the group
    response = client.get(f"/groups/{group['id']}", headers=auth_header(token_owner))
    member_ids = [m["id"] for m in response.get_json()["group"]["members"]]
    assert bob["id"] not in member_ids


def test_leave_group_not_member(client):
    token = get_token(client)
    group = create_group(client, token).get_json()["group"]

    token_bob = signup(client, name="Bob", email="bob@example.com").get_json()["access_token"]

    response = client.delete(f"/groups/{group['id']}/leave", headers=auth_header(token_bob))
    assert response.status_code == 404

def test_delete_group_with_settlements_and_notifications(client):
    """Deleting a group that has settlements/notifications must not 500."""
    token_owner = get_token(client)
    group = create_group(client, token_owner).get_json()["group"]
    gid = group["id"]

    token_bob = signup(client, name="Bob", email="bob@settlement-delete.test").get_json()["access_token"]
    bob = client.get("/auth/me", headers=auth_header(token_bob)).get_json()["user"]

    client.post(
        f"/groups/{gid}/members",
        json={"user_id": bob["id"]},
        headers=auth_header(token_owner),
    )
    expense = client.post(
        f"/api/groups/{gid}/expenses",
        json={
            "description": "Dinner",
            "amount": "90.00",
            "split_type": "equal",
            "paid_by": group["created_by"],
            "participants": [{"user_id": bob["id"]}],
        },
        headers=auth_header(token_owner),
    )
    assert expense.status_code == 201

    settlement = client.post(
        f"/api/groups/{gid}/settlements",
        json={"payer_id": bob["id"], "payee_id": group["created_by"], "amount": 45.0},
        headers=auth_header(token_bob),
    )
    assert settlement.status_code == 201

    response = client.delete(f"/groups/{gid}", headers=auth_header(token_owner))
    assert response.status_code == 200
    assert response.get_json()["message"] == "Group deleted."
