from typing import Any
from fastapi.testclient import TestClient
from pytest import Session
from sqlmodel import select
from src.api import MindplexUser
from src.models import Room, User
from ..fixtures import *


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

        print("data")
        for d in data:
            print(d["id"])

        print("private_rooms")
        for d in private_rooms:
            print(d.id)

        print("public_rooms")
        for d in public_rooms:
            print(d.id)

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

    def test_rooms_filter_peer__id(
        self,
        token: str,
        client: TestClient,
        users,
        dave_unlinked_rooms,
        dave_1_private_room,
        dave_2_private_room,

    ):
        response = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"peer__id": users[1].id}
        )
        assert response.status_code == 200
        data = response.json()

        print("data: ", [room["id"] for room in data])
        print("dave_unlinked_rooms: ", [room.id for room in dave_unlinked_rooms])

        assert len(data) == len(dave_1_private_room)
        for room in data:
            assert room["id"] in [room.id for room in dave_1_private_room]
            assert room["id"] not in [room.id for room in dave_2_private_room]

        response2 = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"peer__id": users[2].id}
        )

        assert response2.status_code == 200
        data = response2.json()


        assert len(data) == len(dave_2_private_room)

    def test_pagination(
            self,
            token: str,
            client: TestClient,
            a_lot_of_rooms: list[Room],
    ):
        # offset 0
        response = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"limit": 5, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # offset 5
        response2 = client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"limit": 50, "offset": 60}
        )
        assert response2.status_code == 200
        data = response2.json()
        assert len(data) == 40

class TestGetRoom:
    def test_auth(self, token: dict[str, Any], client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "test_user"
            }
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(f"/rooms/{rooms[0].id}", headers={
            "Authorization": "",
            "X-Username": "test_user"
        }
    )
        assert response.status_code == 401

    def test_non_existing_room(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 404

    def test_existing_room_with_no_participation_or_ownership(
        self, token: dict[str, Any], client: TestClient, rooms: list[Room]
    ):
        # should work for public rooms
        response = client.get(
            f"/rooms/{rooms[0].id}", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 200

        # should fail for private rooms
        response = client.get(
            f"/rooms/{rooms[1].id}", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
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
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/messages", headers={"Authorization": "", "X-Username": "test_user"}
        )
        print("details: ", response.json())
        assert response.status_code == 401

    def test_non_existing_room(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 404

    def test_existing_room_with_no_access(
        self,
        token: dict[str, Any],
        client: TestClient,
        rooms: list[Room],
    ):
        # should work for public rooms
        response = client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 200

        # should fail for private rooms
        response = client.get(
            f"/rooms/{rooms[1].id}/messages",
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
            f"/rooms/{rooms_with_mindplex[0].id}/messages",
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
            f"/rooms/{rooms_with_mindplex[1].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []


class TestGetRoomParticipants:
    def test_auth(self, token: dict[str, Any], client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code != 401

    def test_no_auth(self, client: TestClient, rooms: list[Room]):
        response = client.get(
            f"/rooms/{rooms[0].id}/participants", headers={"Authorization": "", "X-Username": "test_user"}
        )
        assert response.status_code == 401

    def test_non_existing_room(self, token: dict[str, Any], client: TestClient):
        response = client.get(
            f"/rooms/invalid_room_id/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 404

    def test_existing_room_with_no_access(
        self,
        token: dict[str, Any],
        client: TestClient,
        rooms: list[Room],
    ):
        # should work for public rooms
        response = client.get(
            f"/rooms/{rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 200

        # should fail for private rooms
        response = client.get(
            f"/rooms/{rooms[1].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 403

    def test_room_with_ownership_access(
        self,
        token: dict[str, Any],
        client: TestClient,
        dave_owned_rooms: list[Room],
    ):
        response = client.get(
            f"/rooms/{dave_owned_rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_room_response_with_participants(self, token, client, dave_participated_rooms):
        response = client.get(
            f"/rooms/{dave_participated_rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(dave_participated_rooms[0].participants)

        for participant in data:
            assert participant["id"] in [
                participant.id for participant in dave_participated_rooms[0].participants
            ]

        response2 = client.get(
            f"/rooms/{dave_participated_rooms[1].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2) == len(dave_participated_rooms[1].participants)

        for participant in data2:
            assert participant["id"] in [
                participant.id for participant in dave_participated_rooms[1].participants
            ]

        response3 = client.get(
            f"/rooms/{dave_participated_rooms[2].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response3.status_code == 200
        data3 = response3.json()
        assert len(data3) == len(dave_participated_rooms[2].participants)

        for participant in data3:
            assert participant["id"] in [
                participant.id for participant in dave_participated_rooms[2].participants
            ]

    def test_room_response_with_messages(self, token, client, room_with_messages: list[Room]):
        response = client.get(
            f"/rooms/{room_with_messages[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        

        response2 = client.get(
            f"/rooms/{room_with_messages[1].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response2.status_code == 200
        data2 = response2.json()
        print("data2")
        for d in data2:
            print(d["id"])

        print("room_with_messages")
        for d in room_with_messages[1].messages:
            print(d.owner.id)


        assert len(data2) == 1


    def test_room_response_with_messages_and_participants(self, token, client, dave_participated_rooms):
        pass











