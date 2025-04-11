from datetime import datetime, timedelta
import uuid
import pytest
from src.api import Mindplex, MindplexUser
from src.models import RoomType, SQLModel, Room, User, Message, engine
from sqlmodel import create_engine, Session
from src.main import app
from fastapi.testclient import TestClient
import httpx
import pytest_asyncio


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture(name="engine")
def engine_fixture():
    # Create an in-memory SQLite database
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
    user = User(remote_id="dave")
    user1 = User(remote_id="ivan2")
    user2 = User(remote_id="tony")
    session.add(user)
    session.add(user1)
    session.add(user2)
    session.commit()

    return [user, user1, user2]


@pytest.fixture(name="mindplex_users")
def mindplex_users_fixture():
    return {
        "dave": MindplexUser(
            **{
                "username": "dave",
                "first_name": "dave",
                "last_name": "dave",
                "avatar_url": "https://secure.gravatar.com/avatar/5e9ebd86529dcac05164aacedf030ac7?s=96&d=mm&r=g",
            }
        ),
        "ivan2": MindplexUser(
            **{
                "username": "ivan2",
                "first_name": "ivan",
                "last_name": "ivan",
                "avatar_url": "https://secure.gravatar.com/avatar/5e9ebd86529dcac05164aacedf030ac7?s=96&d=mm&r=g",
            }
        ),
    }


@pytest.fixture(name="rooms")
def rooms_fixture(session: Session, users: list[User]):
    assert users[0].id and users[1].id
    room = Room(owner_id=users[0].id)
    room1 = Room(room_type=RoomType.PRIVATE, owner_id=users[1].id)
    session.add(room)
    session.add(room1)
    session.commit()

    return [room, room1]


@pytest_asyncio.fixture(name="rooms_with_mindplex")
async def rooms_with_mindplex_users_fixture(
    session: Session, mindplex_users: dict[str, MindplexUser]
):
    mpx_sdk = Mindplex()
    user1 = User(remote_id=await mpx_sdk.get_user_id(mindplex_users["dave"]))
    user2 = User(remote_id=await mpx_sdk.get_user_id(mindplex_users["ivan2"]))
    assert user1.id and user2.id
    room = Room(owner_id=user1.id)
    room2 = Room(room_type=RoomType.PRIVATE, owner_id=user2.id, participants=[user1])
    room3 = Room(room_type=RoomType.PRIVATE, owner_id=user2.id)
    session.add(user1)
    session.add(user2)
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()
    
    
    return [room, room2, room3]

@pytest.fixture(name="expired_rooms")
def expired_rooms_fixture(session: Session, users: list[User]):
    assert users[0].id
    room = Room(owner_id=users[0].id, last_interacted=datetime.now() - timedelta(seconds=100))
    room2 = Room(owner_id=users[0].id, last_interacted=datetime.now() - timedelta(seconds=200))
    room3 = Room(owner_id=users[0].id, last_interacted=datetime.now() - timedelta(seconds=300))
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]

@pytest.fixture(name="unexpired_rooms")
def unexpired_rooms_fixture(session: Session, users: list[User]):
    assert users[0].id
    room = Room(owner_id=users[0].id, last_interacted=datetime.now() + timedelta(seconds=100))
    room2 = Room(owner_id=users[0].id, last_interacted=datetime.now() + timedelta(seconds=200))
    room3 = Room(owner_id=users[0].id, last_interacted=datetime.now() + timedelta(seconds=300))
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]
    

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


@pytest.fixture(name="token")
def user_token_fixture():

    url = "https://staging.mindplex.ai/wp-json/auth/v1/token"

    payload = {
        "username":"dave",
        "password":"iBD9xSztMP8C!WglcdzyH2bq",
        "login_with":"email_password",
        "login_from" : "Android"
    }

    # Send the request
    response = httpx.post(url, data=payload)

    return response.json()['token']


@pytest.fixture(name="tony_token")
def tony_token_fixture():

    url = "https://staging.mindplex.ai/wp-json/auth/v1/token"

    payload = {
        "username": "ivan",
        "password": "ivan",
    }

    # Send the request
    response = httpx.post(url, data=payload)

    return response.json()
