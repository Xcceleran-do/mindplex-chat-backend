import os
from typing import Annotated
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
)
from contextlib import asynccontextmanager
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, and_, or_, select
import dotenv
from .dependencies import get_session, get_user_dep
from . import sock
from .models import (
    RoomCreate,
    RoomNotFoundException,
    RoomParticipantLink,
    RoomType,
    User,
    Room,
    Message,
    SQLModel,
    UserNotFoundException,
    engine,
)
from .tasks import remove_expired_rooms_once
from datetime import datetime, timedelta

dotenv.load_dotenv()


DEFAULT_UNIVERSAL_GROUP_EXPIRY = 10 * 60

@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(sock.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def remove_expired_rooms(request, call_next):
    await remove_expired_rooms_once(DEFAULT_UNIVERSAL_GROUP_EXPIRY)
    response = await call_next(request)
    return response


@app.get("/rooms/", response_model=list[Room])
async def get_rooms(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
    private: bool = False,
    owned: bool = False,
):
    # await remove_expired_rooms_once(5)

    query = (
        select(Room)
        .where(
            or_(
                Room.last_interacted > datetime.now() - timedelta(seconds=DEFAULT_UNIVERSAL_GROUP_EXPIRY),
                Room.room_type == RoomType.PRIVATE
            )
        )
    )

    query = (
        query
        .join(RoomParticipantLink, isouter=True)
        .where(
            or_(
                Room.owner_id == user.id,
                RoomParticipantLink.user_id == user.id,
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
async def create_room(
    room: RoomCreate,
    user: Annotated[User, Depends(get_user_dep)],
    session: Annotated[Session, Depends(get_session)],
):

    # await remove_expired_rooms_once(60)

    if room.room_type == RoomType.PRIVATE:
        if len(room.participants) == 0 or len(room.participants) > 1:
            raise HTTPException(
                status_code=400, detail="Private room must have exactly one participant"
            )
    try:
        room_dict = room.model_dump()
        participants = room_dict.pop("participants")

        for participant in participants:
            try:
                user = await User.from_remote_or_db(participant, session)
            except UserNotFoundException:
                raise HTTPException(status_code=400, detail="Participant not found")

        db_room: Room = Room(**room_dict, owner=user)
        session.add(db_room)
        session.commit()
        session.refresh(db_room)
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail="room already exists")

    return db_room


@app.get("/rooms/{room_id}", response_model=Room)
async def get_room(
    room_id: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
):

    # await remove_expired_rooms_once(60)

    try:
        room = await Room.get_by_id(room_id, session, raise_exc=True)
        assert room
    except RoomNotFoundException:
        raise HTTPException(status_code=404, detail="Room not found")
    except AssertionError:  # Just in case
        raise HTTPException(status_code=404, detail="Room not found")

    print(f"requested_user: {user}")

    if not await room.is_in_room(user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    assert room is not None
    return room


@app.post("/rooms/{room_id}/interaction", response_model=Room)
async def update_room_interaction(
    room_id: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
):
    room = await Room.get_by_id(room_id, session, raise_exc=True)
    assert room

    room.last_interacted = datetime.now()
    session.commit()
    session.refresh(room)

    return room

@app.get("/rooms/{room_id}/message", response_model=list[Message])
async def get_room_messages(
    room_id: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
):

    # await remove_expired_rooms_once(60)

    room = await Room.get_by_id(room_id, session, raise_exc=False)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await room.is_in_room(user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    assert room is not None
    return room.messages
