from typing import Any
from fastapi.testclient import TestClient
from src.models import User
from ..fixtures import *

class TestGetUsers:
    def test_auth(self, token: dict[str, Any], client: TestClient, users: list[User]):
        username = users[1].remote_id
        response = client.get(
            f"/users/{username}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.status_code == 200

    def test_no_auth(self, token: str, client: TestClient):
        response = client.get("/users/dave")
        print(response.json())
        assert response.is_client_error
    
    def test_get_user_by_valid_username(self, client: TestClient, token: str, users: list[User]):
        username = users[1].remote_id
        response = client.get(
            f"/users/{username}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.status_code == 200
        assert response.json()["remote_id"] == username 

    def test_get_user_by_invalid_username(self, client: TestClient, token: dict[str, Any]):
        response = client.get(
            f"/users/invalid_usernameabc123",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.is_client_error
    
    def test_get_user_by_mp_username(self, client: TestClient, token: dict[str, Any]):
        response = client.get(
            f"/users/ivan2",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        data = response.json()
        assert response.status_code == 200
        assert data["remote_id"] == "ivan2" 


class TestGetMe:
    def test_auth(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )
        assert response.status_code == 200

    def test_no_auth(self, client: TestClient):
        response = client.get("/users/me")
        assert response.is_client_error

    def test_valid_me(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )
        print(response.json())
        assert response.status_code == 200

        data = response.json()
        assert data["remote_id"] == "dave"


