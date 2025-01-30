import jwt
from fastapi import FastAPI, HTTPException, Depends, Body, Header
from sqlalchemy.orm import Session
from sqlmodel import Session, select
from typing import Annotated, List

from .models import (
    RoomCreate,
    RoomType,
    User,
    Room,
    Message,
    RoomValidationException,
    engine,
)

app = FastAPI()


JWT_KEY = ""


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
        # Decode and verify the JWT token
        payload = jwt.decode(token, JWT_KEY, algorithms=["HS256", "RS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = User(username=payload["username"])

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# Endpoint to create a room (private or universal)
@app.post("/rooms/", response_model=Room)
def create_room(
    room: RoomCreate,
    user: Annotated[User, Depends(get_user)],
    session: Annotated[Session, Depends(get_session)],
):
    db_room = Room.model_validate(
        room, context={"owner": session.get(User, room.owner_id)}
    )
    session.add(db_room)
    session.commit()
    session.refresh(room)
    return room


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
