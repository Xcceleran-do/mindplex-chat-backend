from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError, model_validator
from fastapi import WebSocket
from sqlmodel import select
from .dependencies import get_session, get_user_from_qp_dep
from .models import Message, Room, RoomType, Session, User, engine
import dotenv

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
                    type=WSMessageType.CONNECTED, message=None, sender=None
                ),
            ).model_dump(exclude_none=True)
        )

        if room_id not in self.active_connections:
            self.active_connections[room_id] = []

        self.active_connections[room_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, room_id: str):
        self.active_connections[room_id].remove(websocket)

    async def send_message(
        self, message: "Message", room_id: str, websocket: WebSocket
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
                await connection.send_json(
                    WSResponse(
                        success=True,
                        message=WSMessage(
                            type=WSMessageType.TEXT, message=message, sender=None
                        )
                    ).model_dump(exclude_none=True)
                )


class WSMessageType(str, Enum):
    TEXT = "text"
    CONNECTED = "connected"
    SENT_CONFIRMATION = "sent_confirmation"


class WSMessage(BaseModel):
    type: WSMessageType
    message: Optional[Message | str] 
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


connections = ConnectionManager()


@router.websocket("/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    # session: Session = Depends(get_session),
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
    user_id = user.remote_id

    with Session(engine) as session:
        room_for_validation = await Room.get_by_id(room_id, session, raise_exc=False)

        # check if room exists
        if room_for_validation is None:
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
        if not await room_for_validation.is_user_in_room(user) and room_for_validation.room_type == RoomType.PRIVATE:
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

        assert room_for_validation.id

    await connections.connect(websocket, room_id)

    try:
        while True:
            message_json = await websocket.receive_json()
            try:
                data = WSMessage(**message_json)
            except ValidationError as ve:
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

            with Session(engine) as session:

                room = await Room.get_by_id(room_id, session, raise_exc=True)
                user = await User.from_remote_or_db(user_id, session)  # user must exist in local db
                assert room

                message = Message(owner=user, text=data.message)

                await room.add_message(message)
                session.add(message)
                session.commit()
                session.refresh(message)
                session.refresh(user)
                session.refresh(room)


            await connections.send_message(message, room_id, websocket)
            await websocket.send_json(
                WSResponse(
                    success=True,
                    message=WSMessage(
                        type=WSMessageType.SENT_CONFIRMATION, message=message, sender=user
                    ),
                ).model_dump(exclude_none=True)
            )

    except WebSocketDisconnect:
        print("A user has disconnected: ", websocket)
        await connections.disconnect(websocket, room_id)
        # return session
        session.close()




