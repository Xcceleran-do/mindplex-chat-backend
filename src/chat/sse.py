from enum import Enum
from typing import Optional

from src.dependencies import get_user_dep, get_user_from_qp_dep
from ..models import User, engine, Session, Message, Room
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio


router = APIRouter(prefix="/sse")


class SSEMessageType(str, Enum):
    TEXT = "text"
    CONNECTED = "connected"


class SSEMessage(BaseModel):
    type: SSEMessageType
    text: Optional[Message | str]

    class Config:
        arbitrary_types_allowed = True


async def message_event_generator(room: Room):
    for msg in room.message_stream():
        yield f"data: This is a Message -> {msg.text}\n\n"


@router.get("/{room_id}/")
async def message_stream(
    room_id: str,
    user_or_err: User | str = Depends(get_user_from_qp_dep),
):

    if type(user_or_err) is str:
        print("user_or_err: ", user_or_err)
        raise HTTPException(
            status_code=401,
            detail=user_or_err
        )

    user = user_or_err

    with Session(engine) as session:
        room = await Room.get_by_id(room_id, session, raise_exc=False)

        if room is None:
            raise HTTPException(
                status_code=404,
                detail="Room not found",
            )

        assert type(user) is User
        if await room.is_user_in_room(session, user) is False:
            raise HTTPException(
                status_code=403,
                detail="User is not in the room",
            )

    return StreamingResponse(
        message_event_generator(room),
        media_type="text/event-stream"
    )



