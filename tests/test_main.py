from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.models import User
from .fixtures import *


class TestCreateRoom:
    def test_auth(self, token: str, client: TestClient):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}"},
            json={"room_type": "universal"},
        )
        print("Headers: ", response.request.headers)
        assert response.status_code == 200

    def test_no_auth(self, client: TestClient):
        response = client.post("/rooms", json={"room_type": "universal"})
        assert response.is_client_error

    def test_universal(self, token: str, client: TestClient):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}"},
            json={"room_type": "universal"},
        )
        data = response.json()

        assert data["room_type"] == "universal"
        assert data["owner_id"]
        assert response.status_code == 200

    def test_private(self, token: str, client: TestClient, users: list[User]):
        # With no participants
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}"},
            json={"room_type": "private"},
        )
        data = response.json()

        assert response.is_client_error
        assert data["detail"] == "Private room must have exactly one participant"

        # with a single participant, not self
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}"},
            json={"room_type": "private", "participants": [users[1].id]},
        )
        assert response.status_code == 200
