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
from sqlmodel import Session, or_, select, delete
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
import asyncio
from datetime import datetime, timedelta, timezone

dotenv.load_dotenv()

UNIVERSAL_GROUP_EXPIRY = 60  # In seconds

async def remove_expired_rooms():
    """Deletes universal rooms that have expired """
    while True:
        try:
            now = datetime.now(timezone.utc)
            expiry_threshold = now - timedelta(seconds=UNIVERSAL_GROUP_EXPIRY)

            with Session(engine) as session:
                stmt = delete(Room).where(Room.last_interacted<expiry_threshold)
                result = session.exec(stmt)
                session.commit()
                print(f"Deleted {result.rowcount} expired rooms.")  # Logs the count of deleted rooms

            await asyncio.sleep(3)
        except KeyboardInterrupt as e:
            break


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLModel.metadata.create_all(engine)
    asyncio.create_task(remove_expired_rooms())
    yield
    if os.getenv("ENV", "") != "dev":
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
async def create_room(
    room: RoomCreate,
    user: Annotated[User, Depends(get_user_dep)],
    session: Annotated[Session, Depends(get_session)],
):

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
    try:
        room = await Room.get_by_id(room_id, session, raise_exc=True)
        assert room
    except RoomNotFoundException:
        raise HTTPException(status_code=404, detail="Room not found")
    except AssertionError:  # Just in case
        raise HTTPException(status_code=404, detail="Room not found")

    print("is in room: ", await room.is_in_room(user))
    print("user: ", user)
    print("room: ", room) 
    print("room participants: ", room.participants)
    if not await room.is_in_room(user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    assert room is not None
    return room

@app.get("/rooms/{room_id}/message", response_model=list[Message])
async def get_room_messages(
    room_id: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
):

    room = await Room.get_by_id(room_id, session, raise_exc=False)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await room.is_in_room(user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    assert room is not None
    return room.messages
