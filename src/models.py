from datetime import datetime
from enum import Enum
import os
import json
from typing import Annotated, Generator, Optional
from pydantic import BaseModel
from sqlmodel import (
    Relationship,
    Field,
    SQLModel,
    Session,
    UniqueConstraint,
    create_engine,
    select,
)
from .api import MindplexUser, Mindplex, MindplexApiException
import psycopg2
from psycopg2 import OperationalError
import secrets
import time
from confluent_kafka import Producer, Consumer, KafkaException, KafkaError


POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT")
POSTGRES_USER = os.environ.get("POSTGRES_USER")

TEST_POSTGRES_PASSWORD = os.environ.get("TEST_POSTGRES_PASSWORD")
TEST_POSTGRES_HOST = os.environ.get("TEST_POSTGRES_HOST")
TEST_POSTGRES_DB = os.environ.get("TEST_POSTGRES_DB")
TEST_POSTGRES_PORT = os.environ.get("TEST_POSTGRES_PORT")
TEST_POSTGRES_USER = os.environ.get("TEST_POSTGRES_USER")


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

if os.environ["ENVIRONMENT"] == "test": 
    engine = create_engine(
        f"postgresql://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/{TEST_POSTGRES_DB}",
        pool_size=10,
        max_overflow=20
   )
else:
    engine = create_engine(f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
        pool_size=10,
        max_overflow=20
   )

# Helpers

def wait_for_postgres(host, port, db, user, password, timeout=30):
    start = time.time()
    while True:
        try:
            conn = psycopg2.connect(
                dbname=db,
                user=user,
                password=password,
                host=host,
                port=port,
            )
            conn.close()
            break
        except OperationalError as e:
            if time.time() - start > timeout:
                raise e
            print("Waiting for PostgreSQL...")
            time.sleep(1)


def generate_id():
    # TODO: check for id duplication
    return secrets.token_hex(8)


class RoomType(str, Enum):
    UNIVERSAL = "universal"
    PRIVATE = "private"


class RoomParticipantLink(SQLModel, table=True):
    user_id: str | None = Field(default=None, foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    room_id: str | None = Field(default=None, foreign_key="room.id", primary_key=True, ondelete="CASCADE")


class RoomMessagesLink(SQLModel, table=True):
    message_id: str | None = Field(
        default=None, foreign_key="message.id", primary_key=True, ondelete="CASCADE"
    )
    room_id: str | None = Field(default=None, foreign_key="room.id", primary_key=True, ondelete="CASCADE")


class User(SQLModel, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    remote_id: str = Field(unique=True)

    rooms: list["Room"] = Relationship(
        back_populates="participants", link_model=RoomParticipantLink
    )
    owned_rooms: list["Room"] = Relationship(
        back_populates="owner", cascade_delete=True
    )
    messages: list["Message"] = Relationship(back_populates="owner")

    _table_args__ = (UniqueConstraint("id", "remote_id"),)

    def all_rooms(self) -> list["Room"]:
        """Returns a list of rooms where the user is either a participant or the owner"""
        return self.rooms + self.owned_rooms

    @classmethod
    async def from_remote_or_db(cls, remote_id, session: Session) -> "User":
        """gets a user from remote servers or the local database respectively

        Args:
            remote_id (str): the mindplex(or any user providing service) id
            session (Session): the session to use

        Returns:
            User: the user

        Raises:
            UserNotFoundException: if the user is not found in both remote server and local
            db
        """

        user = session.exec(select(User).where(User.remote_id == remote_id)).first()

        if user is not None:
            return user

        # get user from mindplex
        mpx_sdk = Mindplex()
        try:
            remote_user = await mpx_sdk.get_user(remote_id)
            user = User(remote_id=await mpx_sdk.get_user_id(remote_user))
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except MindplexApiException:
            # TODO: log error
            raise UserNotFoundException(
                f"User with remote id {remote_id} not found"
            )


class RoomBase(SQLModel):
    room_type: RoomType = Field(default=RoomType.UNIVERSAL)


class Room(RoomBase, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)

    participants: list[User] = Relationship(
        back_populates="rooms", link_model=RoomParticipantLink
    )
    messages: list["Message"] = Relationship(
        back_populates="rooms", link_model=RoomMessagesLink
    )

    owner_id: str = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="owned_rooms")
    created: datetime = Field(default_factory=datetime.now)
    last_interacted: datetime = Field(default_factory=datetime.now)

    __kafka_topic_prefix__ = "room"
    __kafka_group_prefix__ = "group"

    def kafka_topic(self):
        return f"{self.__kafka_topic_prefix__}-{self.id}"

    def kafka_group(self):
        return f"{self.__kafka_group_prefix__}-{self.id}"



    async def add_participant(self, participant: "User"):
        """add a participant to the room and commit to db.

        Raises:
            RoomValidationException: if the participant is already in the room
            RoomValidationException: if the room is private and the room has > 2 participants
        """
        if self.room_type == RoomType.PRIVATE and await self.is_user_in_room(participant):
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
        if (
            not await self.is_user_in_room(message.owner)
            and not (self.room_type == RoomType.UNIVERSAL)
        ):
            raise RoomValidationException("User is not in the room")

        self.messages.append(message)

        return message

    async def is_message_in_room(self, message: "Message"):
        return message in self.messages

    async def is_user_in_room(self, user: "User"):
        """checks if a user is in the room as a participant or owner

        Args:
            user (User): the user to check

        Returns:
            bool: True if the user is in the room
        """
        return (
                user in self.participants 
                or user.id == self.owner_id 
                or self.room_type == RoomType.UNIVERSAL
        )

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

    async def send_message(self, message: "Message"):
        """send a message to a kafka topic representing the room. make sure
        that the message in question is refreshed before sending as this might
        cause a race condition.

        Args:
            message (Message): the message to send

        Raises:
            RoomValidationException: if the message is not in the room
            RoomNotFoundException: if the room is not found in the database

        Returns:
            Message: the message that is sent
        """

        producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

        if not await self.is_message_in_room(message):
            raise RoomValidationException("Message is not in the room")

        if self.id == None:
            raise RoomNotFoundException("room id is not set")

        if message.id == None:
            raise MessageNotFoundException("message id is not set")

        producer.produce(
            self.kafka_topic(),
            json.dumps(
                {
                    "type": "text",
                    "message_id": message.id
                }
            ).encode('utf-8')
        )
        producer.flush()
        return {"status": "message sent"}

    def message_stream(self) -> Generator[Optional["Message"], None, None]:
        """ Generates a stream of messages from a kafka topic representing the room

        Yields:
            Message: the message


        """
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': self.kafka_group(),
            'auto.offset.reset': 'earliest'
        })
    
        consumer.subscribe([self.kafka_topic()])
    
        try:
            while True:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue
                if msg.error():
                    # don't crash if the topic does not exist
                    if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        yield None
                        break
                    raise KafkaException(msg.error())

                msg = json.loads(msg.value().decode('utf-8'))

                with Session(engine) as session:
                    message = session.exec(select(Message).where(Message.id == msg["message_id"])).first()
                    yield message
        finally:
            consumer.close()


class RoomCreate(RoomBase):
    participants: list[str] = Field(default=[])


class Message(SQLModel, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    text: str
    created: datetime = Field(default_factory=datetime.now)

    owner_id: str = Field(default=None, foreign_key="user.id", ondelete="CASCADE")
    owner: User = Relationship(back_populates="messages")

    # room_id: str | None = Field(default=None, foreign_key="room.id")
    rooms: list[Room] = Relationship(
        back_populates="messages", link_model=RoomMessagesLink
    )

# Exceptions

class RoomValidationException(Exception):
    pass


class RoomNotFoundException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class MessageNotFoundException(Exception):
    pass


if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)


