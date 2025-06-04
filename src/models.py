from datetime import datetime
from enum import Enum
import os
import json
from typing import Any, AsyncGenerator, Optional
from pydantic import field_serializer
from sqlmodel import (
    Relationship,
    Field,
    SQLModel,
    Session,
    UniqueConstraint,
    create_engine,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from .api import Mindplex, MindplexApiException
import psycopg2
from psycopg2 import OperationalError
import secrets
import time
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio


POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

engine = create_async_engine(f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
    pool_size=10,
    max_overflow=20,
    echo=True
)

# Helpers

async def wait_for_postgres(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        db=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        timeout=30
):
    start = time.time()
    print("Connecting to PostgreSQL...")
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
            print("Connected to PostgreSQL")
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


class RoomTopicStatus(str, Enum):
    NOT_CREATED = "not_created"
    PENDING = "pending"
    CREATED = "created"
    EXISTS = "exists"


class RoomParticipantLink(SQLModel, table=True):
    user_id: str | None = Field(default=None, foreign_key="user.id", primary_key=True, ondelete="CASCADE")
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
    async def from_remote_or_db(cls, remote_id, session: AsyncSession) -> "User":
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

        user = await session.execute(select(User).where(User.remote_id == remote_id))
        user = user.scalars().first()

        if user is not None:
            return user

        # get user from mindplex
        mpx_sdk = Mindplex()
        try:
            remote_user = await mpx_sdk.get_user(remote_id)
            user = User(remote_id=await mpx_sdk.get_user_id(remote_user))
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except MindplexApiException:
            raise UserNotFoundException(
                # TODO: log error
                f"User with remote id {remote_id} not found"
            )


class RoomBase(SQLModel):
    room_type: RoomType = Field(default=RoomType.UNIVERSAL)

# with session decorator
def with_session(func, *args, **kwargs):
    async def wrapper(*args, **kwargs):
        session = kwargs.pop("session", None)

        if session is None:
            async with AsyncSession(engine) as session:
                return await func(*args, session=session, **kwargs)
        else:
            return await func(*args, session=session, **kwargs)

    return wrapper


class Room(RoomBase, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    participants: list[User] = Relationship(
        back_populates="rooms", link_model=RoomParticipantLink
    )
    messages: list["Message"] = Relationship(back_populates="room")
    owner_id: str = Field(foreign_key="user.id", ondelete="CASCADE")
    owner: User = Relationship(back_populates="owned_rooms")
    created: datetime = Field(default_factory=datetime.now)
    last_interacted: datetime = Field(default_factory=datetime.now)

    __kafka_topic_prefix__: str = "room"
    __kafka_group_prefix__: str = "group"

    # @with_session
    async def add_participant(self, session: Session, participant: "User"):
        """add a participant to the room and commit to db.

        Raises:
            RoomValidationException: if the participant is already in the room
            RoomValidationException: if the room is private and the room has > 2 participants
        """

        if self.room_type == RoomType.PRIVATE and await self.is_user_in_room(session, participant):
            raise RoomValidationException("Participant is already in the room")

        if self.room_type == RoomType.PRIVATE and len(self.participants) == 1:
            raise RoomValidationException("Room is private")

        room_participant = RoomParticipantLink(user_id=participant.id, room_id=self.id)
        session.add(room_participant)
        session.commit()

    async def add_message(self, session: Session, message: "Message"):
        """**Deprecated** add a message to the room.

        Args:
            message (Message): the message to add

        Raises:
            RoomValidationException: if the message is None, not the room owner
            or not a participant

        Returns:
            Message: the message that is added
        """
        if (
            not await self.is_user_in_room(session, message.owner)
            and not (self.room_type == RoomType.UNIVERSAL)
        ):
            raise RoomValidationException("User is not in the room")

        self.messages.append(message)

        return message

    async def is_message_in_room(self, message: "Message"):
        return message in self.messages

    async def is_user_in_room(self, session: AsyncSession, user: "User"):
        """checks if a user is in the room as a participant or owner

        Args:
            user (User): the user to check

        Returns:
            bool: True if the user is in the room
        """
        participant_stmt = (
            select(User)
            .join(RoomParticipantLink)
            .where(Room.id == self.id)
        )
        participants = session.exec(participant_stmt).all()

        return (
            user.id in [participant.id for participant in participants]
            or user.id == self.owner_id 
            or self.room_type == RoomType.UNIVERSAL
        )

    @classmethod
    async def get_by_id(
        cls,
        room_id: str,
        session: AsyncSession,
        raise_exc: bool=True
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
        room = await session.execute(select(cls).where(cls.id == room_id))
        room = room.scalars().first()

        if room is None and raise_exc:
            raise RoomNotFoundException("Room not found")
        return room

    async def send_message(self, messages: list["Message"]):
        """send a message to a kafka topic representing the room. make sure
        that the message in question is refreshed before sending as this might
        cause a race condition.

        Args:
            message (Message): the message to send

        Raises:
            MessageNotFoundException: if the message id is not set(did not persist)
            RoomValidationException: if the message is not in the room
            RoomNotFoundException: if the room is not found in the database

        Returns:
            Message: the message that is sent
        """

        producer = await self.kafka_producer()

        try:
            for message in messages:
                if message.id == None:
                    raise MessageNotFoundException("message id is not set")

                if not await self.is_message_in_room(message):
                    raise RoomValidationException("Message is not in the room")

                if self.id == None:
                    raise RoomNotFoundException("room id is not set")

                # Produce message
                await producer.send_and_wait(
                    self.kafka_topic_name(),
                    json.dumps(
                        {
                            "type": "text",
                            "message_id": message.id
                        }
                    ).encode('utf-8')
                )
        finally:
            # Wait for all pending messages to be delivered or expire.
            await producer.stop()

        return messages

    async def message_stream(self, user: "User") -> AsyncGenerator["Message"]:
        """ Generates a stream of messages from a kafka topic representing the room

        Yields:
            Message: the message
        """
        consumer = await self.kafka_consumer()

        try:
            # Consume messages
            async for msg in consumer:
                msg = json.loads(msg.value.decode('utf-8'))
                with AsyncSession(engine) as session:
                    message = session.exec(
                        select(Message).where(Message.id == msg["message_id"])).first()
                    assert message is not None

                    if message.owner_id == user.id:
                        continue
                    else:
                        yield message
        finally:
            # Will leave consumer group; perform autocommit if enabled.
            await consumer.stop()

    def kafka_topic_name(self):
        return f"{self.__kafka_topic_prefix__}-{self.id}"

    def kafka_group_name(self):
        return f"{self.__kafka_group_prefix__}-{self.id}"

    async def kafka_consumer(self):
        consumer = AIOKafkaConsumer(
            self.kafka_topic_name(),
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="fastapi-kafka",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        # Get cluster layout and join group `my-group`
        await consumer.start()

        timeout = time.time() + 10

        while self.kafka_topic_name() not in await consumer.topics():
            await asyncio.sleep(0.1)
            if time.time() > timeout:
                raise Exception("Topic not found")


        return consumer

    async def kafka_producer(self):
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        )

        await producer.start()

        return producer


class RoomCreate(RoomBase):
    participants: list[str] = Field(default=[])


class MessageBase(SQLModel):
    text: str


class MessageCreate(MessageBase):
    pass


class Message(MessageBase, table=True):
    id: str | None = Field(default_factory=generate_id, primary_key=True)
    created: datetime = Field(default_factory=datetime.now)

    owner_id: str = Field(foreign_key="user.id", ondelete="CASCADE")
    owner: User = Relationship(back_populates="messages")

    room_id: str = Field(foreign_key="room.id", ondelete="CASCADE")
    room: Room = Relationship(back_populates="messages")


    # serialize 'created'
    @field_serializer("created")
    def serialize_created(self, value: datetime) -> str:
        return value.isoformat()


class RoomNotFoundException(Exception):
    pass


class RoomValidationException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class MessageNotFoundException(Exception):
    pass


