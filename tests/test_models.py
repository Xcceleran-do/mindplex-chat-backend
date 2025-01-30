from sqlalchemy.inspection import exc
from src.models import RoomType, RoomValidationException, SQLModel, Room, User, Message
from fastapi.testclient import TestClient
from src.main import app
import pytest
from sqlmodel import create_engine, Session


@pytest.fixture(name="engine")
def engine_fixture():
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine):
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[Session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="users")
def users_fixture(session: Session):
    user = User(username="testuser")
    user1 = User(username="testuser1")
    user2 = User(username="testuser2")
    session.add(user)
    session.add(user1)
    session.add(user2)
    session.commit()

    return [user, user1, user2]


@pytest.fixture(name="rooms")
def rooms_fixture(session: Session, users: list[User]):
    room = Room(owner=users[0])
    room1 = Room(room_type=RoomType.PRIVATE, owner=users[1])
    session.add(room)
    session.add(room1)
    session.commit()

    return [room, room1]


@pytest.fixture(name="messages")
def message_fixture(session: Session, users: list[User], rooms: list[Room]):
    message = Message(text="test message", owner=users[0])
    message2 = Message(text="Hello world", owner=users[0])
    message3 = Message(text="Whats up", owner=users[0])
    message4 = Message(text="", owner=users[1])
    message5 = Message(text="Bye!!!", owner=users[1])
    message6 = Message(text="another message", owner=users[2])
    message7 = Message(text="yet another message", owner=users[2])
    session.add(message)
    session.add(message2)
    session.add(message3)
    session.add(message4)
    session.add(message5)
    session.add(message6)
    session.add(message7)
    session.commit()

    return {
        "0": [message, message2, message3],
        "1": [message4, message5],
        "2": [message6, message7],
    }


class TestUser:

    def test_all_rooms(self, session: Session, users: list[User], rooms: list[Room]):

        # Check owner
        assert users[0].all_rooms() == [rooms[0]]

        # Add user as participant
        rooms[0].add_participant(users[1])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]


class TestRoom:
    def test_add_participant(
        self, session: Session, users: list[User], rooms: list[Room]
    ):

        # Check adding multiple users
        assert users[0].all_rooms() == [rooms[0]]  # User already exists as owner
        assert users[1].all_rooms() == [rooms[1]]  # User already exists as owner(room2)
        assert users[2].all_rooms() == []

        rooms[0].add_participant(users[1])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]
        assert users[2].all_rooms() == []

        rooms[0].add_participant(users[2])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]
        assert users[2].all_rooms() == [rooms[0]]

        # Check adding the same user twice
        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            rooms[0].add_participant(users[0])
            session.commit()
        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "Participant is already in the room"

        # Check adding a third user to a private room
        rooms[1].add_participant(users[0])
        session.commit()
        assert rooms[1].participants == [users[0]]
        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            rooms[1].add_participant(users[2])
            session.commit()
        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "Room is private"

    def test_add_message(
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
            rooms[0].add_message(messages.get("1", [])[0])
            session.commit()

        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "User is not in the room"

        rooms[0].add_participant(users[1])
        session.commit()

        message = rooms[0].add_message(messages.get("0", [])[0])
        session.commit()

        assert message
        assert message.owner == users[0]
        assert message in rooms[0].messages

    def test_is_in_room(self, session: Session, users: list[User], rooms: list[Room]):
        assert rooms[0].is_in_room(users[0])
        assert not rooms[0].is_in_room(users[1])
        assert not rooms[0].is_in_room(users[2])

        rooms[0].add_participant(users[1])
        session.commit()

        assert rooms[0].is_in_room(users[0])
        assert rooms[0].is_in_room(users[1])
        assert not rooms[0].is_in_room(users[2])

        rooms[0].add_participant(users[2])
        session.commit()

        assert rooms[0].is_in_room(users[0])
        assert rooms[0].is_in_room(users[1])
        assert rooms[0].is_in_room(users[2])
