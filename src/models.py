from datetime import datetime
from enum import Enum
from sqlmodel import Relationship, Field, SQLModel, create_engine
import secrets


# Helpers
def generate_id():
    # TODO: check for id duplication
    return secrets.token_hex(8)


class RoomType(str, Enum):
    UNIVERSAL = "universal"
    PRIVATE = "private"


class User(SQLModel, table=True):
    id: int | None = Field(default_factory=generate_id, primary_key=True)
    username: str = Field(default="", max_length=50)
    mindplex_id: str | None = Field(default=None)
    keyclock_id: str | None = Field(default=None)


class RoomParticipantLink(SQLModel, table=True):
    user_id: int = Field(default=None, foreign_key="user.id", primary_key=True)
    room_id: int = Field(default=None, foreign_key="room.id", primary_key=True)


class RoomMessagesLink(SQLModel, table=True):
    message_id: int = Field(default=None, foreign_key="message.id", primary_key=True)
    room_id: int = Field(default=None, foreign_key="room.id", primary_key=True)


class Room(SQLModel, table=True):
    id: int | None = Field(default_factory=generate_id, primary_key=True)
    room_type: RoomType = Field(default=RoomType.UNIVERSAL)
    owner: int = Relationship(back_populates="room")
    participants: list[User] = Relationship(
        back_populates="room", link_model=RoomParticipantLink
    )
    messages: list["Message"] = Relationship(
        back_populates="room", link_model=RoomMessagesLink
    )


class Message(SQLModel, table=True):
    id: int | None = Field(default_factory=generate_id, primary_key=True)
    text: str
    created: datetime = Field(default_factory=datetime.now)
    owner: int = Relationship(back_populates="message")
    room: int = Relationship(back_populates="message")


if __name__ == "__main__":
    # Run migrations here
    engine = create_engine("sqlite:///mindplex-chat.db")
    SQLModel.metadata.create_all(engine)
