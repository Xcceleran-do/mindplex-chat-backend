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

    def test_private(
        self, token: str, client: TestClient, keyclock_users: dict[str, KeyclockUser]
    ):
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
            json={
                "room_type": "private",
                "participants": [str(keyclock_users["dave"].id)],
            },
        )
        print("Response data", response.json())
        assert response.status_code == 200

    def test_private_with_no_participants(self, token: str, client: TestClient):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}"},
            json={"room_type": "private", "participants": []},
        )
        assert response.status_code == 400

    def test_private_with_multiple_participants(
        self, token: str, client: TestClient, keyclock_users: dict[str, KeyclockUser]
    ):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "room_type": "private",
                "participants": [
                    str(keyclock_users["dave"].id),
                    str(keyclock_users["dave"].id),
                ],
            },
        )
        assert response.status_code == 400
