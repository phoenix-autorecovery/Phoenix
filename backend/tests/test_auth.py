from fastapi import status

def test_register_and_login(client):
    # Register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@phoenix.io", "password": "securepassword123", "full_name": "New User"}
    )
    assert reg_resp.status_code == status.HTTP_200_OK
    data = reg_resp.json()
    assert data["email"] == "newuser@phoenix.io"
    assert "id" in data

    # Login
    login_resp = client.post(
        "/api/v1/auth/token",
        data={"username": "newuser@phoenix.io", "password": "securepassword123"}
    )
    assert login_resp.status_code == status.HTTP_200_OK
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"

def test_login_invalid_password(client, dev_user):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": dev_user.email, "password": "wrongpassword"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_me(client, dev_token):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {dev_token}"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["email"] == "test_dev@phoenix.io"

def test_unauthorized_access(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
