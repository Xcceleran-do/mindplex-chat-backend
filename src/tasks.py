import asyncio
from datetime import datetime, timedelta, timezone
from src.models import engine, Session, Room
from sqlmodel import delete
from celery import Celery


UNIVERSAL_GROUP_EXPIRY = 60  # In seconds

async def remove_expired_rooms_once(expiry):
    print("Removing expired rooms")
    now = datetime.now(timezone.utc)
    expiry_threshold = now - timedelta(seconds=expiry)

    with Session(engine) as session:
        stmt = delete(Room).where(Room.last_interacted < expiry_threshold)
        result = session.exec(stmt)
        session.commit()

    print(f"Removed {result.rowcount} rooms")

    # await asyncio.sleep(1)

async def remove_expired_rooms_task():
    """Deletes universal rooms that have expired """
    while True:
        await remove_expired_rooms_once(UNIVERSAL_GROUP_EXPIRY)

