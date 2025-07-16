import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from src.models import engine, Session, Room, RoomType
from sqlmodel import delete, or_, and_


async def remove_expired_rooms_once(expiry, session: AsyncSession):

    stmt = delete(Room).where(
        and_(
            Room.last_interacted < datetime.now() - timedelta(seconds=expiry),
            Room.room_type == RoomType.UNIVERSAL
        )
    )

    result = await session.execute(stmt)
    await session.commit()

    print(f"Removed {result.rowcount} expired universal rooms")
