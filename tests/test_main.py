from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlmodel import select

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


class TestGetRoom:
    def test_auth(self, token: str, client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(f"/rooms/{rooms[0].id}", headers={"Authorization": ""})
        assert response.status_code == 401

    def test_non_existing_room(self, token: str, client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_existing_room_with_no_participation_or_ownership(
        self, token: str, client: TestClient, rooms: list[Room]
    ):
        response = client.get(
            f"/rooms/{rooms[0].id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    def test_existing_room_with_ownership(
        self,
        token: str,
        session: Session,
        client: TestClient,
        rooms_with_keyclock: list[Room],
        keyclock_users: dict[str, KeyclockUser],
    ):
        response = client.get(
            f"/rooms/{rooms_with_keyclock[0].id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["id"] == rooms_with_keyclock[0].id
        # assert data["owner_id"] == str(keyclock_users["dave"].id)

        owner_user = session.exec(
            select(User).where(User.id == data["owner_id"])
        ).first()
        assert owner_user

        assert owner_user.keyclock_id == str(keyclock_users["dave"].id)

    def test_existing_room_with_participation(
        self,
        token: str,
        session: Session,
        client: TestClient,
        rooms_with_keyclock: list[Room],
        keyclock_users: dict[str, KeyclockUser],
    ):
        response = client.get(
            f"/rooms/{rooms_with_keyclock[1].id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert response.status_code == 200
        assert data["id"] == rooms_with_keyclock[1].id

        non_owner_user = session.exec(
            select(User).where(User.id == data["owner_id"])
        ).first()
        assert non_owner_user

        assert non_owner_user.keyclock_id != str(keyclock_users["dave"].id)


class TestGetRoomMessages:
    def test_auth(self, token: str, client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/message",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/message", headers={"Authorization": ""}
        )
        assert response.status_code == 401

    def test_non_existing_room(self, token: str, client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id/message",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_existing_room_with_no_access(
        self,
        token: str,
        client: TestClient,
        rooms: list[Room],
        keyclock_users: dict[str, KeyclockUser],
    ):
        response = client.get(
            f"/rooms/{rooms[0].id}/message",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_existing_room_with_ownership_access(
        self,
        token: str,
        session: Session,
        client: TestClient,
        rooms_with_keyclock: list[Room],
        keyclock_users: dict[str, KeyclockUser],
    ):
        response = client.get(
            f"/rooms/{rooms_with_keyclock[0].id}/message",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []

    def test_existing_room_with_participatory_access(
        self,
        token: str,
        session: Session,
        client: TestClient,
        rooms_with_keyclock: list[Room],
        keyclock_users: dict[str, KeyclockUser],
    ):

        response = client.get(
            f"/rooms/{rooms_with_keyclock[1].id}/message",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []
