from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_filter import FilterDepends
from sqlmodel import Session, or_, select
from sqlalchemy.exc import IntegrityError

from ..dependencies import get_session, get_user_dep, DEFAULT_UNIVERSAL_GROUP_EXPIRY
from ..models import Room, RoomCreate, RoomNotFoundException, RoomParticipantLink, RoomType, RoomValidationException, User, UserNotFoundException, Message, MessageCreate
from ..filters import MessageFilter, RoomFilter
from sqlalchemy.dialects import postgresql  # or the appropriate dialect you're using


router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
)


@router.get("/", response_model=list[Room])
async def get_rooms(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
    filter: RoomFilter = FilterDepends(RoomFilter), 
    participant__id: Annotated[Optional[str], Query()] = None,
    peer__id: Annotated[Optional[str], Query()] = None,
    limit: Annotated[Optional[int], Query()] = None,
    offset: Annotated[Optional[int], Query()] = None
):

    query = (
        select(Room)
        .join(
            User,
            User.id == Room.owner_id,
        )
        .join(
            RoomParticipantLink,
            RoomParticipantLink.room_id == Room.id,
            isouter=True
        )
        .where(
            # must be public or recently interacted
            or_(
                Room.last_interacted > datetime.now() - timedelta(seconds=DEFAULT_UNIVERSAL_GROUP_EXPIRY),
                Room.room_type == RoomType.PRIVATE
            ),
            # must be owner or participant
            or_(
                Room.room_type == RoomType.UNIVERSAL,
                Room.owner_id == user.id,
                RoomParticipantLink.user_id == user.id,
            )
        )
    )

    if participant__id is not None:
        query = query.where(RoomParticipantLink.user_id == participant__id).distinct()

    query = filter.filter(query)

    rooms = session.exec(query).all()

    # in memory filters, have low cost but change back to sql when possible for efficiency
    if peer__id is not None:
        rooms = [
            room for room in rooms if (
                (
                    peer__id in [participant.id for participant in room.participants]
                    or peer__id == room.owner_id
                )
                and room.room_type == RoomType.PRIVATE
            )
        ]

    # in memory pagination, change back to sql when possible
    if offset is None:
        offset = 0

    if limit is not None:
        rooms = rooms[offset:offset+limit]


    return rooms


@router.post("/", response_model=Room)
async def create_room(
    room: RoomCreate,
    user: Annotated[User, Depends(get_user_dep)],
    session: Annotated[Session, Depends(get_session)],
):

    if room.room_type == RoomType.PRIVATE:
        if len(room.participants) == 0 or len(room.participants) > 1:
            raise HTTPException(
                status_code=400,
                detail="Private room must have exactly one participant"
            )
    try:
        room_dict = room.model_dump()
        participants = room_dict.pop("participants")
        room_dict["participants"] = []

        for participant in participants:
            try:
                remote_user = await User.from_remote_or_db(participant, session)
                room_dict["participants"].append(remote_user)
            except UserNotFoundException:
                raise HTTPException(status_code=400, detail="Participant not found")

        db_room: Room = Room(**room_dict, owner=user)
        session.add(db_room)
        session.commit()
        session.refresh(db_room)
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail="room already exists")

    return db_room


@router.get("/{room_id}", response_model=Room)
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

    if not await room.is_user_in_room(session, user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    assert room is not None
    return room


@router.post("/{room_id}/interaction", response_model=Room)
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


@router.get("/{room_id}/participants", response_model=list[User])
async def get_room_participants(
    room_id: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
):

    room = await Room.get_by_id(room_id, session, raise_exc=False)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await room.is_user_in_room(session, user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    # get all message senders
    # TODO: currently in memory, use sql
    message_senders = []
    if room.room_type == RoomType.UNIVERSAL:
        message_senders_ = [message.owner for message in room.messages if message.owner != user]
        for message_sender in message_senders_:
            if message_sender not in message_senders:
                message_senders.append(message_sender)

    assert room is not None
    all_participants = room.participants
    all_participants.extend(message_senders)

    return all_participants


@router.get("/{room_id}/messages", response_model=list[Message])
async def get_room_messages(
    room_id: str,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
    filter: MessageFilter = FilterDepends(MessageFilter),
    offset: Annotated[Optional[int], Query()] = None,
    limit: Annotated[Optional[int], Query()] = None
):

    room = await Room.get_by_id(room_id, session, raise_exc=False)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not await room.is_user_in_room(session, user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
    )

    assert room is not None

    query = (
        select(Message)
            .where(Message.room_id == room_id)
    )

    query = filter.filter(query)

    # paginate

    if offset is None:
        offset = 0

    if limit is not None:
        query = query.limit(limit)
        query = query.offset(offset)

    messages = session.exec(query).all()

    return messages


@router.post("/{room_id}/messages", response_model=Message)
async def send_message(
    room_id: str,
    message: MessageCreate,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_user_dep)],
):
    try:
        room = await Room.get_by_id(room_id, session, raise_exc=True)
    except RoomNotFoundException:
        raise HTTPException(status_code=404, detail="Room does not exist")

    assert room

    if not await room.is_user_in_room(session, user):
        raise HTTPException(
            status_code=403, detail="User does not have access to this room"
        )

    try:
        db_message = Message(**message.model_dump(), owner=user, room=room)
        room.last_interacted = datetime.now()  # update last interacted

        session.add(db_message)
        session.add(room)
        session.commit()
        session.refresh(db_message)
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail="message already exists")


    # send message to kafka
    _ = await room.send_message([db_message])

    return db_message



