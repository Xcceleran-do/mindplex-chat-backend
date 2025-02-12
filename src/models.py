from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel
from socketio.pubsub_manager import uuid
from sqlmodel import Relationship, Field, SQLModel, Session, UniqueConstraint, create_engine, select
from .api import Keyclock, KeyclockApiException
import secrets


engine = create_engine("sqlite:///mindplex-chat.db")


# Helpers
def generate_id():
    # TODO: check for id duplication
    return secrets.token_hex(8)


# Exceptions
class RoomValidationException(Exception):
    pass


class RoomNotFoundException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class RoomType(str, Enum):
    UNIVERSAL = "universal"
    PRIVATE = "private"


class RoomParticipantLink(SQLModel, table=True):
    user_id: str | None = Field(default=None, foreign_key="user.id", primary_key=True)
    room_id: str | None = Field(default=None, foreign_key="room.id", primary_key=True)


class RoomMessagesLink(SQLModel, table=True):
    message_id: str | None = Field(
        default=None, foreign_key="message.id", primary_key=True
    )
    room_id: str | None = Field(default=None, foreign_key="room.id", primary_key=True)


class User(SQLModel, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    keyclock_id: str = Field(unique=True)

    rooms: list["Room"] = Relationship(
        back_populates="participants", link_model=RoomParticipantLink
    )
    owned_rooms: list["Room"] = Relationship(
        back_populates="owner",
    )
    messages: list["Message"] = Relationship(back_populates="owner")

    _table_args__ = (UniqueConstraint("id", "keyclock_id"),)

    def all_rooms(self) -> list["Room"]:
        """Returns a list of rooms where the user is either a participant or the owner"""
        return self.rooms + self.owned_rooms

    @classmethod
    async def from_keyclock_or_db(cls, keyclock_id, session: Session) -> "User":
        """gets a user from keyclock or the local database respectively

        Args:
            keyclock_id (str): the keycloak id
            session (Session): the session to use

        Returns:
            User: the user

        Raises:
            UserNotFoundException: if the user is not found in both keyclock and local
            db
        """

        user = session.exec(select(User).where(User.keyclock_id == keyclock_id)).first()

        if user is not None:
            return user

        # get user from keycloack
        kc_api = Keyclock()
        try:
            keyclock_user = await kc_api.get_user(keyclock_id)
            user = User(keyclock_id=str(keyclock_user.id))
            return user
        except KeyclockApiException:
            # TODO: log error
            raise UserNotFoundException(
                f"User with keyclock id {keyclock_id} not found"
            )


class RoomBase(SQLModel):
    room_type: RoomType = Field(default=RoomType.UNIVERSAL)


class Room(RoomBase, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    # room_type: RoomType = Field(default=RoomType.UNIVERSAL)

    participants: list[User] = Relationship(
        back_populates="rooms", link_model=RoomParticipantLink
    )
    messages: list["Message"] = Relationship(
        back_populates="rooms", link_model=RoomMessagesLink
    )

    owner_id: str = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="owned_rooms")
    created: datetime = Field(default_factory=datetime.now)

    async def add_participant(self, participant: "User"):
        """add a participant to the room and commit to db.

        Raises:
            RoomValidationException: if the participant is already in the room
            RoomValidationException: if the room is private and the room has > 2 participants
        """
        if await self.is_in_room(participant):
            raise RoomValidationException("Participant is already in the room")

        if self.room_type == RoomType.PRIVATE and len(self.participants) == 1:
            raise RoomValidationException("Room is private")

        self.participants.append(participant)

    async def add_message(self, message: "Message"):
        """add a message to the room.

        Args:
            message (Message): the message to add

        Raises:
            RoomValidationException: if the message is None, not the room owner
            or not a participant

        Returns:
            Message: the message that is added
        """
        if not await self.is_in_room(message.owner):
            raise RoomValidationException("User is not in the room")

        self.messages.append(message)

        return message

    async def is_in_room(self, user: "User"):
        """checks if a user is in the room as a participant or owner

        Args:
            user (User): the user to check

        Returns:
            bool: True if the user is in the room
        """
        return user in self.participants or user.id == self.owner_id

    @classmethod
    async def get_by_id(
        cls, room_id: str, session: Session, raise_exc: bool = True
    ) -> Optional["Room"]:
        """Gets a room by id

        Args:
            room_id (str): the id of the room
            session (Session): the session to use
            raise_exc (bool, optional): whether to raise an exception if the room \
            is not found. Defaults to True.

        Raises:
            RoomNotFoundException: if the room is not found and raise_exc is True

        Returns:
            Room: the room
            None: if the room is not found and raise_exc is False
        """
        room = session.exec(select(cls).where(cls.id == room_id)).first()
        if room is None and raise_exc:
            raise RoomNotFoundException("Room not found")
        return room


class RoomCreate(RoomBase):
    participants: list[str] = Field(default=[])


class Message(SQLModel, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    text: str
    created: datetime = Field(default_factory=datetime.now)

    owner_id: str = Field(default=None, foreign_key="user.id")
    owner: User = Relationship(back_populates="messages")

    # room_id: str | None = Field(default=None, foreign_key="room.id")
    rooms: list[Room] = Relationship(
        back_populates="messages", link_model=RoomMessagesLink
    )


if __name__ == "__main__":
    # Run migrations here
    SQLModel.metadata.create_all(engine)
