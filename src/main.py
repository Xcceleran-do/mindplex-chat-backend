from fastapi import FastAPI, HTTPException, Depends, Body, Header
from contextlib import asynccontextmanager
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session
from sqlmodel import Session, select
from typing import Annotated, List
import jwt
import json
import base64
import dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


from .models import (
    RoomCreate,
    User,
    Room,
    SQLModel,
    engine,
)

dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


app = FastAPI(lifespan=lifespan)


JWT_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAr+gOQGmyRCXO7UWGT9ub
Pap1jn+HFDk6i7RGXNQQagpan0OvDmo26IpT/fL9QfUpIvz+TaWRw+n171oduqK0
Qksv/hjHVYnHB+EcZ6TlyebTk1wCXxDTs0XLH2ugbSJtnhida/JBToeMzcArfPbU
ag6ZqBjNQqQXXe+gUvG8Ln0U9ZLfclz9NDqebdcHeVnQ+L4mOJiXHz5CHOcfPRhW
YI+rXIDC1zylWeQV0Dxcd0JThaVWnpiJA+ciBZzs9Hnf9zlaw63mS4sRBGGbjonx
tVe8eFWj9KDa7XbeQf6bG5T0Vfh8hLcwtg8jgkE+6IrrVR3HHHHEC/9JyoBsIrcZ
bwIDAQAB
-----END PUBLIC KEY-----
"""


def get_session():
    with Session(engine) as session:
        yield session


# Dependency to validate JWT and return the user
def get_user(
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = authorization.split(" ")[1]  # Extract the actual token

    try:
        # Verify the JWT using the public key
        payload = jwt.decode(
            token,
            JWT_KEY,
            algorithms=["RS256"],  # Ensure this matches the algorithm in the JWT header
            options={
                "verify_aud": False
            },  # Disable audience verification for this example
        )

    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # get or create the user
    user = session.exec(
        select(User).where(User.username == payload["preferred_username"])
    ).first()
    print("User: ", user)

    if user is None:
        user = User(username=payload["preferred_username"])
        session.add(user)
        session.commit()
        session.refresh(user)

    return user

@app.get("/rooms/", response_model=List[Room])
def get_rooms(session: Annotated[Session, Depends(get_session)]):
    return session.exec(select(Room)).all()

# Endpoint to create a room (private or universal)
@app.post("/rooms/", response_model=Room)
def create_room(
    room: RoomCreate,
    user: Annotated[User, Depends(get_user)],
    session: Annotated[Session, Depends(get_session)],
):
    db_room: Room = Room.model_validate(room, context={"owner": user})
    session.add(db_room)
    session.commit()
    session.refresh(db_room)
    return db_room


#
# # Endpoint to add a participant to a room
# @app.post("/rooms/{room_id}/participants/")
# def add_participant_to_room(room_id: str, user_id: str, db: Session = Depends(get_db)):
#     room = db.query(Room).filter(Room.id == room_id).first()
#     if room is None:
#         raise HTTPException(status_code=404, detail="Room not found")
#
#     user = get_user_by_id(db, user_id)
#
#     try:
#         room.add_participant(user)
#         db.commit()
#     except RoomValidationException as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#     return {"message": "Participant added successfully"}
#
#
# # Endpoint to send a message to a room
# @app.post("/rooms/{room_id}/messages/")
# def send_message(room_id: str, user_id: str, text: str, db: Session = Depends(get_db)):
#     room = db.query(Room).filter(Room.id == room_id).first()
#     if room is None:
#         raise HTTPException(status_code=404, detail="Room not found")
#
#     user = get_user_by_id(db, user_id)
#
#     if not room.is_in_room(user):
#         raise HTTPException(status_code=400, detail="User is not in the room")
#
#     message = Message(text=text, owner_id=user.id)
#     try:
#         room.add_message(message)
#         db.commit()
#     except RoomValidationException as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#     db.refresh(message)
#     return message
#
#
# # Endpoint to create a private chat (room with only two participants)
# @app.post("/private_chat/")
# def create_private_chat(user1_id: str, user2_id: str, db: Session = Depends(get_db)):
#     user1 = get_user_by_id(db, user1_id)
#     user2 = get_user_by_id(db, user2_id)
#
#     room = Room(room_type=RoomType.PRIVATE)
#     room.add_participant(user1)
#     room.add_participant(user2)
#
#     db.add(room)
#     db.commit()
#     db.refresh(room)
#
#     return room
#
#
# # Endpoint to retrieve all rooms a user is part of
# @app.get("/users/{user_id}/rooms/", response_model=List[Room])
# def get_rooms_for_user(user_id: str, db: Session = Depends(get_db)):
#     user = get_user_by_id(db, user_id)
#     rooms = user.all_rooms()
#     return rooms
#
#
# # Endpoint to retrieve all messages in a room
# @app.get("/rooms/{room_id}/messages/", response_model=List[Message])
# def get_messages_in_room(room_id: str, db: Session = Depends(get_db)):
#     room = db.query(Room).filter(Room.id == room_id).first()
#     if room is None:
#         raise HTTPException(status_code=404, detail="Room not found")
#
#     return room.messages
#
#
# # Endpoint to retrieve all users in a room
# @app.get("/rooms/{room_id}/participants/", response_model=List[User])
# def get_users_in_room(room_id: str, db: Session = Depends(get_db)):
#     room = db.query(Room).filter(Room.id == room_id).first()
#     if room is None:
#         raise HTTPException(status_code=404, detail="Room not found")
#
#     return room.participants
