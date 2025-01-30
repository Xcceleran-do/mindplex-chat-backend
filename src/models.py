from datetime import datetime
from enum import Enum
from sqlmodel import Relationship, Field, SQLModel, Session, create_engine, select
import secrets


engine = create_engine("sqlite:///mindplex-chat.db")


# Helpers
def generate_id():
    # TODO: check for id duplication
    return secrets.token_hex(8)


# Exceptions
class RoomValidationException(Exception):
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
    username: str = Field(default="", max_length=50)
    mindplex_id: str | None = Field(default=None)
    keyclock_id: str | None = Field(default=None)

    rooms: list["Room"] = Relationship(
        back_populates="participants", link_model=RoomParticipantLink
    )
    messages: list["Message"] = Relationship(back_populates="owner")

    def _rooms(self) -> list["Room"]:
        """Returns a list of rooms where the user is either a participant or the owner"""

        with Session(engine) as session:
            room_owned_statement = select(Room).where(Room.owner == self.id)
            room_participated_statement = (
                select(Room)
                .join(RoomParticipantLink)
                .where(RoomParticipantLink.user_id == self.id)
            )

            rooms_owned = list(session.exec(room_owned_statement).all())
            rooms_participated = list(session.exec(room_participated_statement).all())
            rooms = rooms_owned + rooms_participated

            return rooms


class Room(SQLModel, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    room_type: RoomType = Field(default=RoomType.UNIVERSAL)

    participants: list[User] = Relationship(
        back_populates="rooms", link_model=RoomParticipantLink
    )
    messages: list["Message"] = Relationship(
        back_populates="rooms", link_model=RoomMessagesLink
    )

    owner_id: str | None = Field(default=None, foreign_key="user.id")
    owner: User | None = Relationship(back_populates="rooms")

    def add_participant(self, participant: "User"):
        """add a participant to the room and commit to db.

        Raises:
            RoomValidationException: if the participant is already in the room
        """

    def add_message(self, message: "Message"):
        """add a message to the room and commit to db.

        Args:
            message (Message): the message to add

        Raises:
            RoomValidationException: if the message is not from the room owner or is not a participant

        Returns:
            Message: the message that is added
        """

    def is_in_room(self, user: "User"):
        """checks if a user is in the room as a participant or owner

        Args:
            user (User): the user to check

        Returns:
            bool: True if the user is in the room
        """


class Message(SQLModel, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    text: str
    created: datetime = Field(default_factory=datetime.now)

    owner_id: str | None = Field(default=None, foreign_key="user.id")
    owner: User | None = Relationship(back_populates="messages")

    # room_id: str | None = Field(default=None, foreign_key="room.id")
    rooms: list[Room] = Relationship(
        back_populates="messages", link_model=RoomMessagesLink
    )


if __name__ == "__main__":
    # Run migrations here
    SQLModel.metadata.create_all(engine)
