from src.tasks import remove_expired_rooms_once
from src.models import Room, User, Session
from sqlmodel import select
from datetime import datetime, timedelta, timezone
from .fixtures import *

@pytest.mark.asyncio
async def test_remove_expired_rooms_once(session: Session, users: list[User]):
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(seconds=100)
    fresh_time = now

    assert users[0].id

    # Insert 1 expired and 1 fresh room
    session.add(Room(id='1', last_interacted=expired_time, owner_id=users[0].id))
    session.add(Room(id='2', last_interacted=fresh_time, owner_id=users[0].id))
    session.commit()

    await remove_expired_rooms_once(50)

    # Now verify only the fresh room remains
    remaining = session.exec(select(Room)).all()
    assert len(remaining) == 1
    assert remaining[0].id == '2'

