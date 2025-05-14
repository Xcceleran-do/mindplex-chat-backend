import asyncio
from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, ValidationError, model_validator
from fastapi import WebSocket
from sqlmodel import select
from ..dependencies import get_session, get_user_from_qp_dep
from ..models import Message, Room, RoomType, Session, User, engine
import dotenv

dotenv.load_dotenv()

router = APIRouter(prefix="/ws")


class WSMessageType(str, Enum):
    TEXT = "text"
    CONNECTED = "connected"
    SENT_CONFIRMATION = "sent_confirmation"


class WSMessage(BaseModel):
    type: WSMessageType
    message: Optional[Message | str] 

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


@router.websocket("/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
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

        if (
            (not await room_for_validation.is_user_in_room(session, user))
            and room_for_validation.room_type == RoomType.PRIVATE
        ):
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

        # accept connection
        try:
            await websocket.accept()
            await websocket.send_json(
                WSResponse(
                    success=True,
                    message=WSMessage(
                        type=WSMessageType.CONNECTED, message=None
                    ),
                ).model_dump(exclude_none=True)
            )
        except Exception as e:
            print(e)
            return

        async def listen_for_new_messages(websocket: WebSocket, room: Room, user: User = user):
            async for message in room.message_stream(user):
                try:
                    await websocket.send_json(
                        WSResponse(
                            success=True,
                            message=WSMessage(
                                type=WSMessageType.TEXT,
                                message=message,
                            ),
                        ).model_dump(exclude_none=True)
                    )
                except WebSocketDisconnect:
                    return

        try:
            print("Starting listener task")
            listener_task = await asyncio.create_task(
                listen_for_new_messages(websocket, room_for_validation, user)
            )
        finally:
            print("Listener task cancelled")


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

                # room and user should exist here
                room = await Room.get_by_id(room_id, session, raise_exc=True)
                user = await User.from_remote_or_db(user_id, session)  # user must exist in local db
                assert room and room.id
                assert user and user.id
                assert type(data.message) == str

                message = Message(
                    owner_id=user.id,
                    room_id=room.id,
                    text=data.message,
                    room=room
                )

                session.add(message)
                session.commit()
                session.refresh(message)

                await room.send_message([message])
                await websocket.send_json(
                    WSResponse(
                        success=True,
                        message=WSMessage(
                            type=WSMessageType.SENT_CONFIRMATION, message=message
                        ),
                    ).model_dump(exclude_none=True)
                )

    except WebSocketDisconnect:
        # await websocket.close()
        session.close()




