from src.tasks import remove_expired_rooms_once
from src.models import Room, User, Session
from sqlmodel import select
from datetime import datetime, timedelta, timezone
from .fixtures import *

@pytest.mark.asyncio
async def test_remove_expired_rooms_once(session: Session, expired_rooms: list[Room], unexpired_rooms: list[Room]):
    now = datetime.now(timezone.utc)

    await remove_expired_rooms_once(50)

    # Now verify only the fresh room remains
    remaining = session.exec(select(Room)).all()
    assert len(remaining) == len(unexpired_rooms)

    for room in remaining:
        assert room not in expired_rooms

