from datetime import datetime
from typing import Optional
from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_filter import FilterDepends, with_prefix
from .models import RoomType, User, Room, Message


class UserFilter(Filter):
    id: Optional[str] = None
    remote_id: Optional[str] = None

    class Constants(Filter.Constants):
        model = User


class RoomFilter(Filter):
    owner_id: Optional[UserFilter] = FilterDepends(with_prefix("owner", UserFilter))
    room_type: Optional[RoomType] = None

    class Constants(Filter.Constants):
        model = Room


class MessageFilter(Filter):
    owner_id: Optional[str] = None  # TODO: FilterDepends
    created__gt: Optional[datetime] = None
    created__lt: Optional[datetime] = None
    created__gte: Optional[datetime] = None
    created__lte: Optional[datetime] = None

    class Constants(Filter.Constants):
        model = Message
