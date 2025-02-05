import os
from typing import Annotated
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError
import socketio
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, or_, select
import dotenv
from .dependencies import get_session, get_user_dep, get_user, get_user_from_qp_dep
from . import sock
from .models import (
    RoomCreate,
    RoomParticipantLink,
    RoomType,
    User,
    Room,
    Message,
    SQLModel,
    engine,
)


dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


app = FastAPI(lifespan=lifespan)
app.include_router(sock.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/rooms/", response_model=list[Room])
def get_rooms(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
    private: bool = False,
    owned: bool = False,
):
    query = (
        select(Room)
        .join(RoomParticipantLink)
        .where(
            or_(
                Room.owner_id == user.id,
                RoomParticipantLink.user_id == user.id,
                Room.room_type == RoomType.UNIVERSAL,
            )
        )
    )

    if private:
        query = query.where(Room.room_type == RoomType.PRIVATE)
    if owned:
        query = query.where(Room.owner_id == user.id)

    rooms = session.exec(query).all()

    return rooms


# Endpoint to create a room (private or universal)
@app.post("/rooms/", response_model=Room)
def create_room(
    room: RoomCreate,
    user: Annotated[User, Depends(get_user_dep)],
    session: Annotated[Session, Depends(get_session)],
):
    try:
        db_room: Room = Room(**room.model_dump(), owner=user)
        session.add(db_room)
        session.commit()
        session.refresh(db_room)
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail="room already exists")

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
