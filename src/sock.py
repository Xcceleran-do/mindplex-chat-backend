from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError, model_validator
from fastapi import WebSocket
from .dependencies import get_session, get_user, get_user_from_qp_dep
from .models import Message, Room, RoomType, Session, User, engine
import dotenv
import json

dotenv.load_dotenv()

router = APIRouter(prefix="/ws")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, room_id: str):
        self.active_connections[room_id].remove(websocket)

    async def send_message(self, message: str, room_id: str, websocket: WebSocket):
        """
        Send a message to a specific room excluding the sender.

        Args:
            message (str): the message to send
            room_id (str): the room to send the message to
            websocket (WebSocket): the websocket to exclude
        """
        for connection in self.active_connections[room_id]:
            if connection != websocket:
                await connection.send_text(message)


class WSMessageType(str, Enum):
    TEXT = "text"


class WSMessage(BaseModel):
    type: WSMessageType
    message: str

    class Config:
        arbitrary_types_allowed = True


class WSError(BaseModel):
    status_code: int
    short_code: str
    details: str | dict

class WSResponse(BaseModel):
    success: bool
    error: Optional[WSError] = None
    message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def check_success(cls, values):
        if values.success:
            assert values.message
        else:
            assert values.error
        return values


connections = ConnectionManager()


@router.websocket("/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    session: Session = Depends(get_session),
    user_or_err: User | str = Depends(get_user_from_qp_dep),
):

    # check if user is authorized
    if type(user_or_err) is str:
        await websocket.accept()
        response = WSResponse(
            success=False,
            error=WSError(
                status_code=401, short_code="unauthorized", details=user_or_err
            ),
        )
        await websocket.send_json(response.model_dump(exclude_none=True))
        await websocket.close()
        return

    assert type(user_or_err) is User
    user = user_or_err

    room = await Room.get_by_id(room_id, session, raise_exc=False)

    # check if room exists
    if room is None:
        await websocket.accept()
        response = WSResponse(
            success=False,
            error=WSError(
                status_code=404, short_code="not_found", details="room not found"
            ),
        )
        await websocket.send_json(response.model_dump(exclude_none=True))
        await websocket.close()
        return

    # check if user is in room
    if not await room.is_in_room(user) and room.room_type == RoomType.PRIVATE:
        await websocket.accept()
        response = WSResponse(
            success=False,
            error=WSError(
                status_code=403,
                short_code="not_in_room",
                details="user not in private room",
            ),
        )
        await websocket.send_json(response.model_dump(exclude_none=True))
        return

    assert room.id
    await connections.connect(websocket, room.id)
    try:
        while True:
            message_text = await websocket.receive_json()
            try:
                data = WSMessage(**message_text)
            except ValidationError as ve:
                response = WSResponse(
                    success=False,
                    error=WSError(
                        status_code=400,
                        short_code="validation_error",
                        details=json.loads(ve.json()),
                    ),
                )
                await websocket.send_json(response.model_dump(exclude_none=True))
                continue
            message = Message(owner=user, text=data.message)
            await room.add_message(message)
            session.add(message)
            session.commit()
            session.refresh(message)

            await connections.send_message(message_text, room.id, websocket)

    except WebSocketDisconnect:
        await connections.disconnect(websocket, room.id)
