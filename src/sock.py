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
        """Connect websocket to room"""
        await websocket.accept()
        await websocket.send_json(
            WSResponse(
                success=True,
                message=WSMessage(
                    type=WSMessageType.TEXT, message="Connected to room", sender=None
                ),
            ).model_dump(exclude_none=True)
        )

        if room_id not in self.active_connections:
            self.active_connections[room_id] = []

        self.active_connections[room_id].append(websocket)
        print("New Connection: ", self.active_connections)

    async def disconnect(self, websocket: WebSocket, room_id: str):
        self.active_connections[room_id].remove(websocket)

    async def send_message(
        self, message: "WSMessage", room_id: str, websocket: WebSocket
    ):
        """
        Send a message to a specific room excluding the sender.

        Args:
            message (str): the message to send
            room_id (str): the room to send the message to
            websocket (WebSocket): the websocket to exclude
        """

        # raise Exception("Connections: ", self.active_connections)
        for connection in self.active_connections[room_id]:
            if connection != websocket:
                await connection.send_json(message.model_dump(exclude_none=True))


class WSMessageType(str, Enum):
    TEXT = "text"


class WSMessage(BaseModel):
    type: WSMessageType
    message: str
    sender: Optional[User]

    class Config:
        arbitrary_types_allowed = True


class WSError(BaseModel):
    status_code: int
    short_code: str
    details: str | dict


class WSResponse(BaseModel):
    success: bool
    error: Optional[WSError] = None
    message: Optional[WSMessage] = None

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
            message_json = await websocket.receive_json()
            try:
                data = WSMessage(**message_json)
            except ValidationError as ve:
                print(ve.json())
                response = WSResponse(
                    success=False,
                    error=WSError(
                        status_code=400,
                        short_code="validation_error",
                        details=ve.json(),
                    ),
                )
                await websocket.send_json(response.model_dump(exclude_none=True))
                continue

            assert data.message
            message = Message(owner=user, text=data.message)
            await room.add_message(message)
            session.add(message)
            session.commit()
            session.refresh(message)

            await connections.send_message(data, room.id, websocket)

    except WebSocketDisconnect:
        print("A user has disconnected: ", websocket)
        await connections.disconnect(websocket, room.id)



