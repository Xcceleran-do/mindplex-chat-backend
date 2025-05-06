from enum import Enum
from typing import Optional

from src.dependencies import get_user_dep
from ..models import User, engine, Session, Message, Room
from fastapi import APIRouter, Depends
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



async def message_event_generator(room_id: str, user: User):
    room = None
    with Session(engine) as session:
        room = await Room.get_by_id(room_id, session)

    if room is None:
        raise Exception("Room not found")

    for i in range(10):
        # Yield data in SSE format
        yield f"data: This is Message {i}\n\n"
        await asyncio.sleep(1)


@router.get("/{room_id}/")
async def message_stream(
    room_id: str,
    user: User = Depends(get_user_dep)
):
    return StreamingResponse(message_event_generator(room_id, user), media_type="text/event-stream")
