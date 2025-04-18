from typing import Any
from fastapi.testclient import TestClient
from sqlmodel import select

from src.models import User
from src.main import DEFAULT_UNIVERSAL_GROUP_EXPIRY
from .fixtures import *


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

    def test_get_user_by_self_username(self, client: TestClient, token: str):
        response = client.get(
            f"/users/dave",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )

        assert response.status_code == 404
    
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
            f"/users/invalid_username",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.is_client_error


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


class TestCreateRoom:
    def test_auth(self, token: dict[str, Any], client: TestClient):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "universal"},
        )
        assert response.status_code == 200

    def test_no_auth(self, client: TestClient):
        response = client.post("/rooms", json={"room_type": "universal"})
        assert response.is_client_error

    def test_universal(self, token: dict[str, Any], client: TestClient):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "universal"},
        )
        data = response.json()

        assert data["room_type"] == "universal"
        assert data["owner_id"]
        assert response.status_code == 200

    def test_private(
        self, token: dict[str, Any], client: TestClient, mindplex_users: dict[str, MindplexUser]
    ):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "private"},
        )
        data = response.json()

        assert response.is_client_error
        assert data["detail"] == "Private room must have exactly one participant"

        # with a single participant, not self
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={
                "room_type": "private",
                "participants": [str(mindplex_users["dave"].username)],
            },
        )

        assert response.status_code == 200

    def test_private_with_no_participants(self, token: dict[str, Any], client: TestClient):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "private", "participants": []},
        )
        assert response.status_code == 400

    def test_private_with_multiple_participants(
        self, token: dict[str, Any], client: TestClient, mindplex_users: dict[str, MindplexUser]
    ):
        response = client.post(
            "/rooms",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={
                "room_type": "private",
                "participants": [
                    str(mindplex_users["dave"].username),
                    str(mindplex_users["dave"].username),
                ],
            },
        )

        assert response.status_code == 400


class TestGetRooms:
    def test_auth(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            "/rooms/", headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )
        assert response.status_code == 200

    def test_no_auth(self, client: TestClient):
        response = client.get("/rooms/", headers={"Authorization": "", "X-Username": "dave"})
        print("response status: ", response.status_code)
        assert response.status_code == 401

    def test_rooms_filter_room_type(self, token: str, client: TestClient, public_rooms, private_rooms):
        response = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"} ,
            params={"room_type": "private"}
        )

        assert response.status_code == 200
        data = response.json() 

        assert len(data) == len(private_rooms)

        for room in data:
            assert room["id"] in [room.id for room in private_rooms]

        response2 = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"} ,
            params={"room_type": "universal"}
        )

        assert response2.status_code == 200
        data2 = response2.json() 

        assert len(data2) == len(public_rooms)

        for room in data2:
            assert room["id"] in [room.id for room in public_rooms]
    
    def test_rooms_filter_owner__id(
            self,
            token: str,
            client: TestClient,
            users,
            dave_owned_rooms,
            dave_participated_rooms,
            dave_unlinked_rooms
    ):
        response = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"owner__id": users[0].id}
        )
        # print("users: ", users[0].id)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(dave_owned_rooms)


        for room in data:
            assert room["id"] in [room.id for room in dave_owned_rooms]
            assert room["id"] not in [room.id for room in dave_participated_rooms]
            assert room["id"] not in [room.id for room in dave_unlinked_rooms]

    

    def test_rooms_filter_owner__remote_id(
            self,
            token: str,
            client: TestClient,
            users,
            dave_owned_rooms,
            dave_participated_rooms,
            dave_unlinked_rooms
    ):
        response = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"owner__remote_id": "dave"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(dave_owned_rooms)

        for room in data:
            assert room["id"] in [room.id for room in dave_owned_rooms]
            assert room["id"] not in [room.id for room in dave_participated_rooms]
            assert room["id"] not in [room.id for room in dave_unlinked_rooms]


    def test_rooms_filter_participants__user_id(
        self,
        token: str,
        client: TestClient,
        users,
        dave_owned_rooms,
        dave_participated_rooms,
        dave_unlinked_rooms
    ):
        response = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"participant__id": users[0].id}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(dave_participated_rooms)

        for room in data:
            assert room["id"] in [room.id for room in dave_participated_rooms]
            assert room["id"] not in [room.id for room in dave_owned_rooms]
            assert room["id"] not in [room.id for room in dave_unlinked_rooms]


class TestGetRoom:
    def test_auth(self, token: dict[str, Any], client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(f"/rooms/{rooms[0].id}", headers={"Authorization": "", "X-Username": "test_user"})
        assert response.status_code == 401

    def test_non_existing_room(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 404

    def test_existing_room_with_no_participation_or_ownership(
        self, token: dict[str, Any], client: TestClient, rooms: list[Room]
    ):
        response = client.get(
            f"/rooms/{rooms[0].id}", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 403

    def test_existing_room_with_ownership(
        self,
        token: dict[str, Any],
        session: Session,
        client: TestClient,
        rooms_with_mindplex: list[Room],
        mindplex_users: dict[str, MindplexUser],
    ):
        response = client.get(
            f"/rooms/{rooms_with_mindplex[0].id}",
            headers={"Authorization": f"Bearer {token}", "X-Username": mindplex_users["dave"].username},
        )
        data = response.json()

        print(f"to_be_requested_user: {rooms_with_mindplex[0].owner}")

        assert response.status_code == 200
        assert data["id"] == rooms_with_mindplex[0].id
        # assert data["owner_id"] == str(mindplex_users["dave"].username)

        owner_user = session.exec(
            select(User).where(User.id == data["owner_id"])
        ).first()
        assert owner_user

        assert owner_user.remote_id == str(mindplex_users["dave"].username)

    def test_existing_room_with_participation(
        self,
        token: dict[str, Any],
        session: Session,
        client: TestClient,
        rooms_with_mindplex: list[Room],
        mindplex_users: dict[str, MindplexUser],
    ):
        response = client.get(
            f"/rooms/{rooms_with_mindplex[1].id}",
            headers={"Authorization": f"Bearer {token}", "X-Username": mindplex_users["dave"].username},
        )
        data = response.json()
        assert response.status_code == 200
        assert data["id"] == rooms_with_mindplex[1].id

        non_owner_user = session.exec(
            select(User).where(User.id == data["owner_id"])
        ).first()
        assert non_owner_user

        assert non_owner_user.remote_id != str(mindplex_users["dave"].username)

    def test_expired_rooms(
            self,
            token: dict[str, Any],
            client: TestClient,
            expired_rooms: list[Room],
            unexpired_rooms:list[Room],
            mindplex_users: dict[str, MindplexUser]
    ):
        response = client.get(
            f"/rooms",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": mindplex_users["dave"].username
            }
        )

        data = response.json()
        assert response.status_code == 200

        assert len(data) == len(unexpired_rooms)

        for room in data:
            assert room["id"] in [room.id for room in unexpired_rooms]


class TestGetRoomMessages:
    def test_auth(self, token: dict[str, Any], client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/message",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/message", headers={"Authorization": "", "X-Username": "test_user"}
        )
        assert response.status_code == 401

    def test_non_existing_room(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id/message",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 404

    def test_existing_room_with_no_access(
        self,
        token: dict[str, Any],
        client: TestClient,
        rooms: list[Room],
    ):
        response = client.get(
            f"/rooms/{rooms[0].id}/message",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 403

    def test_existing_room_with_ownership_access(
        self,
        token: dict[str, Any],
        session: Session,
        client: TestClient,
        rooms_with_mindplex: list[Room],
        mindplex_users: dict[str, MindplexUser],
    ):
        response = client.get(
            f"/rooms/{rooms_with_mindplex[0].id}/message",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []

    def test_existing_room_with_participatory_access(
        self,
        token: dict[str, Any],
        session: Session,
        client: TestClient,
        rooms_with_mindplex: list[Room],
    ):

        response = client.get(
            f"/rooms/{rooms_with_mindplex[1].id}/message",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []
