from datetime import datetime, timedelta
import pytest
from src.api import Mindplex, MindplexUser
from src.models import RoomType, SQLModel, Room, User, Message, engine, Session 
from src.main import app, DEFAULT_UNIVERSAL_GROUP_EXPIRY
from fastapi.testclient import TestClient
import httpx
import pytest_asyncio

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    # change db
    monkeypatch.setenv("POSTGRES_USER", "test_fastapi")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_secret")
    monkeypatch.setenv("POSTGRES_DB", "test_fastapi_db")
    monkeypatch.setenv("POSTGRES_HOST", "test_db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture(name="engine")
def engine_fixture():
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
    room = Room(owner_id=users[0].id, last_interacted=datetime.now() - timedelta(seconds=100+DEFAULT_UNIVERSAL_GROUP_EXPIRY))
    room2 = Room(owner_id=users[0].id, last_interacted=datetime.now() - timedelta(seconds=200+DEFAULT_UNIVERSAL_GROUP_EXPIRY))
    room3 = Room(owner_id=users[0].id, last_interacted=datetime.now() - timedelta(seconds=300+DEFAULT_UNIVERSAL_GROUP_EXPIRY))
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]


@pytest.fixture(name="unexpired_rooms")
def unexpired_rooms_fixture(session: Session, users: list[User]):
    assert users[0].id
    room = Room(owner_id=users[0].id, last_interacted=datetime.now() + timedelta(seconds=100+DEFAULT_UNIVERSAL_GROUP_EXPIRY))
    room2 = Room(owner_id=users[0].id, last_interacted=datetime.now() + timedelta(seconds=200+DEFAULT_UNIVERSAL_GROUP_EXPIRY))
    room3 = Room(owner_id=users[0].id, last_interacted=datetime.now() + timedelta(seconds=300+DEFAULT_UNIVERSAL_GROUP_EXPIRY))
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]
 

@pytest.fixture(name="private_rooms")
def private_rooms_fixture(session: Session, users: list[User]):
    assert users[0].id
    room = Room(owner_id=users[0].id, room_type=RoomType.PRIVATE)
    room2 = Room(owner_id=users[0].id, room_type=RoomType.PRIVATE)
    room3 = Room(owner_id=users[0].id, room_type=RoomType.PRIVATE)
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]


@pytest.fixture(name="public_rooms")
def public_rooms_fixture(session: Session, users: list[User]):
    assert users[0].id
    room = Room(owner_id=users[0].id)
    room2 = Room(owner_id=users[0].id)
    room3 = Room(owner_id=users[0].id)
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]


@pytest.fixture(name="dave_owned_rooms")
def dave_owned_rooms_fixture(session: Session, users: list[User]):
    assert users[0].id
    room = Room(owner_id=users[0].id)
    room2 = Room(owner_id=users[0].id)
    room3 = Room(owner_id=users[0].id)
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]


@pytest.fixture(name="dave_participated_rooms")
def dave_participated_rooms_fixture(session: Session, users: list[User]):
    assert users[1].id and users[2].id

    room = Room(owner_id=users[1].id, participants=[users[0], users[2]])
    room2 = Room(owner_id=users[1].id, participants=[users[0]])
    room3 = Room(owner_id=users[2].id, participants=[users[0], users[1]])
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]


@pytest.fixture(name="dave_unlinked_rooms")
def dave_unlinked_rooms_fixture(session: Session, users: list[User]):
    assert users[1].id and users[2].id
    room = Room(owner_id=users[1].id)
    room2 = Room(owner_id=users[2].id)
    room3 = Room(owner_id=users[1].id)
    session.add(room)
    session.add(room2)
    session.add(room3)
    session.commit()

    return [room, room2, room3]


@pytest.fixture(name="dave_1_private_room")
def dave_1_private_room_fixture(session: Session, users: list[User]):
    assert users[1].id and users[0].id
    room = Room(owner_id=users[0].id, participants=[users[1]], room_type=RoomType.PRIVATE)
    session.add(room)
    session.commit()

    return [room]


@pytest.fixture(name="dave_2_private_room")
def dave_2_private_room_fixture(session: Session, users: list[User]):
    assert users[2].id and users[0].id
    room = Room(owner_id=users[2].id, participants=[users[0]], room_type=RoomType.PRIVATE)
    session.add(room)
    session.commit()

    return [room]


@pytest.fixture(name="dave_private_rooms")
def dave_private_rooms_fixture(session: Session, users: list[User]):
    assert users[1].id and users[2].id and users[0].id
    room = Room(owner_id=users[0].id, participants=[users[1]], room_type=RoomType.PRIVATE)
    room2 = Room(owner_id=users[2].id, participants=[users[0]], room_type=RoomType.PRIVATE)
    session.add(room)
    session.add(room2)
    session.commit()

    return [room, room2]


@pytest_asyncio.fixture(name="room_with_messages")
async def room_with_messages_fixture(session: Session, users: list[User]):
    assert users[0].id and users[1].id and users[2].id
    room1 = Room(owner_id=users[0].id)
    assert room1.id
    # create messages for room 1

    message1 = Message(text="test message", owner_id=users[0].id, room_id=room1.id)
    message2 = Message(text="Hello world", owner_id=users[0].id, room_id=room1.id)
    message4 = Message(text="", owner_id=users[1].id, room_id=room1.id)
    message6 = Message(text="another message", owner_id=users[2].id, room_id=room1.id)

    room2 = Room(owner_id=users[0].id, room_type=RoomType.PRIVATE, participants=[users[1]])
    assert room2.id
    message3 = Message(text="Whats up", owner_id=users[0].id, room_id=room2.id)
    message5 = Message(text="Bye!!!", owner_id=users[1].id, room_id=room2.id)
    message7 = Message(text="yet another message", owner_id=users[2].id, room_id=room2.id)


    session.add(message1)
    session.add(message2)
    session.add(message3)
    session.add(message4)
    session.add(message5)
    session.add(message6)
    session.add(message7)
    session.add(room1)
    session.add(room2)
    session.commit()

    return [room1, room2]


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


@pytest.fixture(name="a_lot_of_rooms")
def a_lot_of_rooms_fixture(session: Session):
    for i in range(100):
        user = User(remote_id=f"{i}")
        assert user.id
        room = Room(owner_id=user.id)
        session.add(user)
        session.add(room)
    session.commit()
        

@pytest.fixture(name="a_lot_of_messages")
def a_lot_of_messages_fixture(session: Session, users: list[User], rooms: list[Room]):
    all_messages: list[Message] = []
    flip = 1
    for i in range(50):
        room = rooms[0] if i % 2 == 0 else rooms[1]
        message = Message(
            text=f"message {i} by {users[0].remote_id}",
            owner=users[0],
            created=datetime.now()+timedelta(days=i+1),
            room=room
        )
        session.add(message)
        all_messages.append(message)
        flip *= -1
    session.commit()

    flip = 1
    for i in range(50):
        room = rooms[0] if i % 2 == 0 else rooms[1]
        message = Message(
            text=f"message {i} by {users[1].remote_id}",
            owner=users[1],
            created=datetime.now()-timedelta(days=i+1),
            room=room
        )
        session.add(message)
        all_messages.append(message)
        flip *= -1
    session.commit()

    # rooms[0].messages = [msg for (i, msg) in enumerate(all_messages) if i % 2 == 0]  # even
    # rooms[1].messages = [msg for (i, msg) in enumerate(all_messages) if i % 2 == 1]  # odd

    session.commit()

    return all_messages







