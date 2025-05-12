from datetime import datetime
from enum import Enum
import os
import json
from typing import Any, Generator, Optional
from pydantic import PrivateAttr
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
from .api import Mindplex, MindplexApiException
import psycopg2
from psycopg2 import OperationalError
import secrets
import time
from confluent_kafka import Producer, Consumer, KafkaException, KafkaError 
from confluent_kafka.admin import AdminClient, NewTopic


POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

engine = create_engine(f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
    pool_size=10,
    max_overflow=20
)

# Helpers

def wait_for_postgres(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        db=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        timeout=30
):
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
            with Session(engine) as session:
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

    async def is_user_in_room(self, session: Session, user: "User"):
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
        session: Session,
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
        room = session.exec(select(cls).where(cls.id == room_id)).first()
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

        producer = self.kafka_producer()

        for message in messages:
            if message.id == None:
                raise MessageNotFoundException("message id is not set")

            if not await self.is_message_in_room(message):
                raise RoomValidationException("Message is not in the room")

            if self.id == None:
                raise RoomNotFoundException("room id is not set")

            producer.produce(
                self.kafka_topic_name(),
                json.dumps(
                    {
                        "type": "text",
                        "message_id": message.id
                    }
                ).encode('utf-8'),
                callback=self.__class__.ack
            )
            producer.poll(1.0)
        producer.flush()

        return messages

    def message_stream(self) -> Generator["Message", None, None]:
        """ Generates a stream of messages from a kafka topic representing the room

        Yields:
            Message: the message
        """
        print("before kafka subscribe")
        consumer = self.kafka_consumer()
        print("after kafka subscribe")

        try:
            print("entering polling loop")
            while True:
                print("polling kafka")
                msg = consumer.poll(1.0)

                if msg is None:
                    print("no message")
                    continue
                if msg.error():
                    continue
                    raise KafkaException(msg.error())

                print("got message: ", msg.value().decode('utf-8'))
                msg = json.loads(msg.value().decode('utf-8'))

                with Session(engine) as session:
                    print("fetching message from the database")
                    message = session.exec(select(Message).where(Message.id == msg["message_id"])).first()
                    assert message is not None
                    yield message

        except KeyboardInterrupt:
            print("exiting message stream")
            consumer.close()
        finally:
            consumer.close()

    def kafka_topic_name(self):
        return f"{self.__kafka_topic_prefix__}-{self.id}"

    def kafka_group_name(self):
        print("kafka_group: ", f"{self.__kafka_group_prefix__}-{self.id}")
        return f"{self.__kafka_group_prefix__}-{self.id}"

    def kafka_consumer(self):
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': self.kafka_group_name(),
            'auto.offset.reset': 'earliest'
        })

        # check if the topic exists 
        # creates the topic if it doesn't exist
        topic = consumer.list_topics(topic=self.kafka_topic_name()).topics.get(self.kafka_topic_name())
        print("topic_-_: ", topic)

        if topic is None:
            raise KafkaException(f"Topic {self.kafka_topic_name()} does not exist")

        consumer.subscribe([self.kafka_topic_name()])

        return consumer

    def kafka_producer(self):
        return Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

    def create_kafka_topic(self) -> Optional[Any]:
        """ Creates a kafka topic for the room. does nothing if the topic already exists

        Raises:
        """

        admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
        partitions = 2 if self.room_type == RoomType.PRIVATE else 6

        try:
            topic_future = admin_client.create_topics(
                [
                    NewTopic(
                        topic=self.kafka_topic_name(),
                        num_partitions=partitions,
                        replication_factor=1,
                    )
                ]
            )
            topic_future[self.kafka_topic_name()].result(10)

        except KafkaException as ke:
            if ke.args[0].error == KafkaError.TOPIC_ALREADY_EXISTS:
                return None 
            else:
                raise

    @staticmethod
    def ack(err, msg):
        if err is not None:
            print("Failed to deliver message: {}".format(err.str()))
        else:
            print("Message produced: {}".format(msg.topic()))


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


class RoomNotFoundException(Exception):
    pass


class RoomValidationException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class MessageNotFoundException(Exception):
    pass


if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)


