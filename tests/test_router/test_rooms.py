import json
from typing import Any
from fastapi.testclient import TestClient
from pytest import Session
from sqlmodel import select
from src.api import MindplexUser
from src.models import Room, User
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
from ..fixtures import *


class TestCreateRoom:
    @pytest.mark.asyncio
    async def test_auth(
            self,
            token: str,
            client: AsyncClient
    ):
        response = await client.post(
            "/rooms/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"room_type": "universal"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient):
        response = await client.post("/rooms/", json={"room_type": "universal"})

        assert response.is_client_error

    @pytest.mark.asyncio
    async def test_universal(self, token: dict[str, Any], client: AsyncClient):
        response = await client.post(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "universal"},
        )
        data = response.json()

        assert data["room_type"] == "universal"
        assert data["owner_id"]
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_private(
        self,
        token: dict[str, Any],
        client: AsyncClient, mindplex_users: dict[str, MindplexUser]
    ):
        response = await client.post(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "private"},
        )
        data = response.json()

        assert response.is_client_error
        assert data["detail"] == "Private room must have exactly one participant"

        # with a single participant, not self
        response = await client.post(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={
                "room_type": "private",
                "participants": [str(mindplex_users["dave"].username)],
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_private_with_no_participants(self, token: dict[str, Any], client: AsyncClient):
        response = await client.post(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
            json={"room_type": "private", "participants": []},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_private_with_multiple_participants(
        self, token: dict[str, Any], client: AsyncClient, mindplex_users: dict[str, MindplexUser]
    ):
        response = await client.post(
            "/rooms/",
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
    @pytest.mark.asyncio
    async def test_auth(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        session: AsyncSession,
    ):
        response = await client.get(
            "/rooms/", headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth(
        self,
        client: AsyncClient,
        session: AsyncSession,
    ):
        response = await client.get("/rooms/", headers={"Authorization": "", "X-Username": "dave"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rooms_filter_room_type(self, token: str, client: AsyncClient, public_rooms, private_rooms):
        response = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"} ,
            params={"room_type": "private"}
        )

        assert response.status_code == 200
        data = response.json() 

        assert len(data) == len(private_rooms)

        for room in data:
            assert room["id"] in [room.id for room in private_rooms]

        response2 = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"} ,
            params={"room_type": "universal"}
        )

        assert response2.status_code == 200
        data2 = response2.json() 

        assert len(data2) == len(public_rooms)

        for room in data2:
            assert room["id"] in [room.id for room in public_rooms]
    
    @pytest.mark.asyncio
    async def test_rooms_filter_owner__id(
            self,
            token: str,
            client: AsyncClient,
            users,
            dave_owned_rooms,
            dave_participated_rooms,
            dave_unlinked_rooms
    ):
        response = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"owner__id": users[0].id}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(dave_owned_rooms)


        for room in data:
            assert room["id"] in [room.id for room in dave_owned_rooms]
            assert room["id"] not in [room.id for room in dave_participated_rooms]
            assert room["id"] not in [room.id for room in dave_unlinked_rooms]

    @pytest.mark.asyncio
    async def test_rooms_filter_owner__remote_id(
            self,
            token: str,
            client: AsyncClient,
            users,
            dave_owned_rooms,
            dave_participated_rooms,
            dave_unlinked_rooms
    ):
        response = await client.get(
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

    @pytest.mark.asyncio
    async def test_rooms_filter_participants__user_id(
        self,
        token: str,
        client: AsyncClient,
        users,
        dave_owned_rooms,
        dave_participated_rooms,
        dave_unlinked_rooms
    ):
        response = await client.get(
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

    @pytest.mark.asyncio
    async def test_rooms_filter_peer__id(
        self,
        token: str,
        client: AsyncClient,
        users,
        dave_unlinked_rooms,
        dave_1_private_room,
        dave_2_private_room,

    ):
        response = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"peer__id": users[1].id}
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data) == len(dave_1_private_room)
        for room in data:
            assert room["id"] in [room.id for room in dave_1_private_room]
            assert room["id"] not in [room.id for room in dave_2_private_room]

        response2 = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"peer__id": users[2].id}
        )

        assert response2.status_code == 200
        data = response2.json()


        assert len(data) == len(dave_2_private_room)

    @pytest.mark.asyncio
    async def test_pagination(
            self,
            token: str,
            client: AsyncClient,
            a_lot_of_rooms: list[Room],
    ):
        # offset 0
        response = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"limit": 5, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # offset 5
        response2 = await client.get(
            "/rooms/",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"limit": 50, "offset": 60}
        )
        assert response2.status_code == 200
        data = response2.json()
        assert len(data) == 40


class TestGetRoom:
    @pytest.mark.asyncio
    async def test_auth(self, token: dict[str, Any], client: AsyncClient, rooms: list[Room]):
        response = await client.get(
            f"/rooms/{rooms[0].id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "test_user"
            }
        )
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient, rooms: list[Room]):
        response = await client.get(f"/rooms/{rooms[0].id}", headers={
            "Authorization": "",
            "X-Username": "test_user"
        }
    )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_existing_room(self, token: dict[str, Any], client: AsyncClient):
        response = await client.get(
            f"/rooms/invalid_room_id", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_existing_room_with_no_participation_or_ownership(
        self, token: dict[str, Any], client: AsyncClient, rooms: list[Room]
    ):
        # should work for public rooms
        response = await client.get(
            f"/rooms/{rooms[0].id}", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 200

        # should fail for private rooms
        response = await client.get(
            f"/rooms/{rooms[1].id}", headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_existing_room_with_ownership(
        self,
        token: dict[str, Any],
        session: AsyncSession,
        client: AsyncClient,
        rooms_with_mindplex: list[Room],
        mindplex_users: dict[str, MindplexUser],
    ):
        response = await client.get(
            f"/rooms/{rooms_with_mindplex[0].id}",
            headers={"Authorization": f"Bearer {token}", "X-Username": mindplex_users["dave"].username},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["id"] == rooms_with_mindplex[0].id
        # assert data["owner_id"] == str(mindplex_users["dave"].username)

        owner_user = await session.execute(
            select(User).where(User.id == data["owner_id"])
        )
        owner_user = owner_user.scalars().first()
        assert owner_user

        assert owner_user.remote_id == str(mindplex_users["dave"].username)

    @pytest.mark.asyncio
    async def test_existing_room_with_participation(
        self,
        token: dict[str, Any],
        session: AsyncSession,
        client: AsyncClient,
        rooms_with_mindplex: list[Room],
        mindplex_users: dict[str, MindplexUser],
    ):
        response = await client.get(
            f"/rooms/{rooms_with_mindplex[1].id}",
            headers={"Authorization": f"Bearer {token}", "X-Username": mindplex_users["dave"].username},
        )
        data = response.json()
        assert response.status_code == 200
        assert data["id"] == rooms_with_mindplex[1].id

        non_owner_user = await session.execute(
            select(User).where(User.id == data["owner_id"])
        )
        non_owner_user = non_owner_user.scalars().first()
        assert non_owner_user

        assert non_owner_user.remote_id != str(mindplex_users["dave"].username)

    @pytest.mark.asyncio
    async def test_expired_rooms(
            self,
            token: dict[str, Any],
            client: AsyncClient,
            expired_rooms: list[Room],
            unexpired_rooms:list[Room],
            mindplex_users: dict[str, MindplexUser]
    ):
        response = await client.get(
            f"/rooms/",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": mindplex_users["dave"].username
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == len(unexpired_rooms)

        for room in data:
            assert room["id"] in [room.id for room in unexpired_rooms]


class TestGetRoomMessages:
    @pytest.mark.asyncio
    async def test_auth(self, token: dict[str, Any], client: AsyncClient, rooms: list[Room]):
        response = await client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient, rooms: list[Room]):
        response = await client.get(
            f"/rooms/{rooms[0].id}/messages", headers={"Authorization": "", "X-Username": "test_user"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_existing_room(self, token: dict[str, Any], client: AsyncClient):
        response = await client.get(
            f"/rooms/invalid_room_id/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_existing_room_with_no_access(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        rooms: list[Room],
    ):
        # should work for public rooms
        response = await client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 200

        # should fail for private rooms
        response = await client.get(
            f"/rooms/{rooms[1].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_existing_room_with_ownership_access(
        self,
        token: dict[str, Any],
        session: Session,
        client: AsyncClient,
        rooms_with_mindplex: list[Room],
        mindplex_users: dict[str, MindplexUser],
    ):
        response = await client.get(
            f"/rooms/{rooms_with_mindplex[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []

    @pytest.mark.asyncio
    async def test_existing_room_with_participatory_access(
        self,
        token: dict[str, Any],
        session: Session,
        client: AsyncClient,
        rooms_with_mindplex: list[Room],
    ):

        response = await client.get(
            f"/rooms/{rooms_with_mindplex[1].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )
        data = response.json()

        assert response.status_code == 200
        assert data == []

    @pytest.mark.asyncio
    async def test_retrieved_message_is_in_room(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        users: list[User],
        rooms: list[Room],
        a_lot_of_messages: list[Message],
        session: AsyncSession
    ):
        # correct messages retrieved
        response = await client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )

        room0_messages_stmt = (
            select(Message)
                .join(Room)
                .where(Room.id == rooms[0].id)
        )         
        room0_messages_result = await session.execute(room0_messages_stmt)
        room0_messages = room0_messages_result.scalars().all()

        room1_messages_stmt = (
            select(Message)
                .join(Room)
                .where(Room.id == rooms[1].id)
        )         
        room1_messages_result = await session.execute(room1_messages_stmt)
        room1_messages = room1_messages_result.scalars().all()

        assert response.status_code == 200

        data = response.json()
        assert len(data) == len(room0_messages)

        for message in data:
            assert message["id"] in [message.id for message in room0_messages]
            assert message["id"] not in [message.id for message in room1_messages]

    @pytest.mark.asyncio
    async def test_owner_filter(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        users: list[User],
        rooms: list[Room],
        a_lot_of_messages: list[Message],
    ):
        response = await client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"owner_id": users[0].id}
        )
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 25

        for message in data:
            assert message["owner_id"] == users[0].id

    @pytest.mark.asyncio
    async def test_created_relational_filters(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        users: list[User],
        rooms: list[Room],
        a_lot_of_messages: list[Message],
    ):
        # created__lt
        response = await client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"created__lt": datetime.now().isoformat()},
        )
        data = response.json()

        assert response.status_code == 200
        assert len(data) == 25

        for message in data:
            assert datetime.fromisoformat(message["created"]) < datetime.now()

        # created__gt
        response2 = await client.get(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            params={"created__gt": datetime.now().isoformat()},
        )
        data2 = response2.json()

        assert response.status_code == 200
        assert len(data2) == 25

        for message in data2:
            assert datetime.fromisoformat(message["created"]) > datetime.now()


class TestGetRoomParticipants:
    @pytest.mark.asyncio
    async def test_auth(self, token: dict[str, Any], client: AsyncClient, rooms: list[Room]):
        response = await client.get(
            f"/rooms/{rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient, rooms: list[Room]):
        response = await client.get(
            f"/rooms/{rooms[0].id}/participants", headers={"Authorization": "", "X-Username": "test_user"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_existing_room(self, token: dict[str, Any], client: AsyncClient):
        response = await client.get(
            f"/rooms/invalid_room_id/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_existing_room_with_no_access(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        rooms: list[Room],
    ):
        # should work for public rooms
        response = await client.get(
            f"/rooms/{rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 200

        # should fail for private rooms
        response = await client.get(
            f"/rooms/{rooms[1].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "test_user"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_room_with_ownership_access(
        self,
        token: dict[str, Any],
        client: AsyncClient,
        dave_owned_rooms: list[Room],
    ):
        response = await client.get(
            f"/rooms/{dave_owned_rooms[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_room_response_with_participants(self, token, client, dave_participated_rooms):
        response = await client.get(
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

        response2 = await client.get(
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

        response3 = await client.get(
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

    @pytest.mark.asyncio
    async def test_room_response_with_messages(self, token, client, room_with_messages: list[Room]):
        response = await client.get(
            f"/rooms/{room_with_messages[0].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        

        response2 = await client.get(
            f"/rooms/{room_with_messages[1].id}/participants",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )

        assert response2.status_code == 200
        data2 = response2.json()

        assert len(data2) == 1

    @pytest.mark.asyncio
    async def test_room_response_with_messages_and_participants(self, token, client, dave_participated_rooms):
        pass


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_message(self, token, client: AsyncClient, session: AsyncSession, rooms: list[Room]):
        response = await client.post(
            f"/rooms/{rooms[0].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            json={"text": "hello world"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "hello world"

        # test message perssists
        db_message = await session.execute(
            select(Message).where(Message.id == data["id"])
        ) 
        db_message = db_message.scalars().first()
        assert db_message
        assert db_message.room_id == rooms[0].id
        assert db_message.text == "hello world"

        # test message sent to kafka
        consumer = await rooms[0].kafka_consumer()
        try:
            kafka_msg = await consumer.getone()
            assert kafka_msg is not None
            assert json.loads(kafka_msg.value.decode('utf-8'))["message_id"] == data["id"]
        finally:
            await consumer.stop()

    @pytest.mark.asyncio
    async def test_user_not_in_room(self, token, client: AsyncClient, rooms):
        response = await client.post(
            f"/rooms/{rooms[1].id}/messages",
            headers={"Authorization": f"Bearer {token}", "X-Username": "dave"},
            json={"text": "hello world"}
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "User does not have access to this room"












