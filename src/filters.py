from typing import Optional
from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_filter import FilterDepends, with_prefix
from .models import RoomType, User, Room, RoomParticipantLink


class UserFilter(Filter):
    id: Optional[str] = None
    remote_id: Optional[str] = None

    class Constants(Filter.Constants):
        model = User

# class RoomParticipantLinkFilter(Filter):
#     user_id: Optional[str] = None
#     # user_remote_id: Optional[str] = None
#
#     class Constants(Filter.Constants):
#         model = RoomParticipantLink

class RoomFilter(Filter):
    owner_id: Optional[UserFilter] = FilterDepends(with_prefix("owner", UserFilter))
    room_type: Optional[RoomType] = None
    # participants: Optional[RoomParticipantLinkFilter] = FilterDepends(
    #     with_prefix(
    #         "participant",
    #         RoomParticipantLinkFilter
    #     )
    # )

    class Constants(Filter.Constants):
        model = Room

