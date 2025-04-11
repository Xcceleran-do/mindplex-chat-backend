from src.models import RoomType, RoomParticipantLink, Room, User, Message
import pytest
from sqlmodel import Session, select, or_
from .fixtures import *


class TestUser:

    @pytest.mark.asyncio
    async def test_all_rooms(
        self, session: Session, users: list[User], rooms: list[Room]
    ):
        # Check owner
        assert users[0].all_rooms() == [rooms[0]]

        # Add user as participant
        await rooms[0].add_participant(users[1])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]


class TestRoom:

    @pytest.mark.asyncio
    async def test_add_participant(
        self, session: Session, users: list[User], rooms: list[Room]
    ):

        # Check adding multiple users
        assert users[0].all_rooms() == [rooms[0]]  # User already exists as owner
        assert users[1].all_rooms() == [rooms[1]]  # User already exists as owner(room2)
        assert users[2].all_rooms() == []

        await rooms[0].add_participant(users[1])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]
        assert users[2].all_rooms() == []

        await rooms[0].add_participant(users[2])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]
        assert users[2].all_rooms() == [rooms[0]]

        # Check adding the same user twice
        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            await rooms[0].add_participant(users[0])
            session.commit()
        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "Participant is already in the room"

        # Check adding a third user to a private room
        await rooms[1].add_participant(users[0])
        session.commit()
        assert rooms[1].participants == [users[0]]
        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            await rooms[1].add_participant(users[2])
            session.commit()
        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "Room is private"

    @pytest.mark.asyncio
    async def test_add_message(
        self,
        session: Session,
        users: list[User],
        rooms: list[Room],
        messages: dict[str, list[Message]],
    ):
        assert rooms[0].messages == []

        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            await rooms[1].add_message(messages.get("2", [])[0])
            session.commit()

        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "User is not in the room"

        await rooms[0].add_participant(users[1])
        session.commit()

        message = await rooms[0].add_message(messages.get("0", [])[0])
        session.commit()

        assert message
        assert message.owner == users[0]
        assert message in rooms[0].messages

    @pytest.mark.asyncio
    async def test_is_in_room(
        self, session: Session, users: list[User], rooms: list[Room]
    ):
        assert await rooms[0].is_in_room(users[0])
        assert not await rooms[0].is_in_room(users[1])
        assert not await rooms[0].is_in_room(users[2])

        await rooms[0].add_participant(users[1])
        session.commit()

        assert await rooms[0].is_in_room(users[0])
        assert await rooms[0].is_in_room(users[1])
        assert not await rooms[0].is_in_room(users[2])

        await rooms[0].add_participant(users[2])
        session.commit()

        assert await rooms[0].is_in_room(users[0])
        assert await rooms[0].is_in_room(users[1])
        assert await rooms[0].is_in_room(users[2])

        assert not await rooms[1].is_in_room(users[0])
        assert await rooms[1].is_in_room(users[1])

    @pytest.mark.asyncio
    async def test_room_expiry(
            self,
            session: Session,
            unexpired_rooms: list[Room],
            expired_rooms: list[Room],
            users: list[User]
    ):

        query = (
            select(Room)
            .where(
                or_(
                    Room.last_interacted > datetime.now() - timedelta(seconds=50),
                    Room.room_type == RoomType.PRIVATE
                )
            )
        )

        queried_rooms = session.exec(query).all()
        assert len(queried_rooms) == len(unexpired_rooms)

        for room in queried_rooms:
            assert room not in expired_rooms





