import asyncio
from datetime import datetime, timedelta, timezone
from src.models import engine, Session, Room, RoomType
from sqlmodel import delete, or_


async def remove_expired_rooms_task(expiry):
    """Deletes universal rooms that have expired """
    while True:
        try:
            await remove_expired_rooms_once(expiry)
        except:
            break


async def remove_expired_rooms_once(expiry):
    print("Removing expired rooms")

    with Session(engine) as session:
        stmt = delete(Room).where(
            or_(
                Room.last_interacted < datetime.now() - timedelta(seconds=expiry),
                Room.room_type == RoomType.PRIVATE
            )
        )

        result = session.exec(stmt)
        session.commit()

    print(f"Removed {result.rowcount} rooms")
