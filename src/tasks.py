import asyncio
from datetime import datetime, timedelta, timezone
from src.models import engine, Session, Room, RoomType
from sqlmodel import delete, or_


UNIVERSAL_GROUP_EXPIRY = 5  # In seconds

class BackgroundTask:
    def __init__(self):
        pass

    def remove_expired_rooms_task(self):
        """Deletes universal rooms that have expired """
        while True:
            try:
                BackgroundTask.remove_expired_rooms_once(UNIVERSAL_GROUP_EXPIRY)
            except:
                break


    @staticmethod
    def remove_expired_rooms_once(expiry):
        print("Removing expired rooms")
        now = datetime.now(timezone.utc)
        expiry_threshold = now - timedelta(seconds=expiry)

        with Session(engine) as session:
            stmt = delete(Room).where(
                or_(
                    Room.last_interacted < datetime.now() - timedelta(seconds=50),
                    Room.room_type == RoomType.PRIVATE
                )
            )

            result = session.exec(stmt)
            session.commit()

        print(f"Removed {result.rowcount} rooms")
