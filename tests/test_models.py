from src.models import RoomTopicStatus, RoomType, RoomParticipantLink, Room, User, Message, RoomValidationException
import pytest
import json
from sqlmodel import Session, select, delete, or_
from .fixtures import *
from confluent_kafka.admin import AdminClient
import threading


class TestUser:

    @pytest.mark.asyncio
    async def test_all_rooms(
        self, session: Session, users: list[User], rooms: list[Room]
    ):
        # Check owner
        assert users[0].all_rooms() == [rooms[0]]

        # Add user as participant
        await rooms[0].add_participant(session, users[1])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]


class TestRoom:

    @pytest.mark.asyncio
    async def test_add_participant(
        self, session: Session, users: list[User], rooms: list[Room]
    ):

        # Check adding multiple users
        assert users[0].all_rooms() == [rooms[0]]  # User already exists as owner
        assert users[1].all_rooms() == [rooms[1]]  # User already exists as owner(room2)
        assert users[2].all_rooms() == []

        await rooms[0].add_participant(session, users[1])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]
        assert users[2].all_rooms() == []

        await rooms[0].add_participant(session, users[2])
        session.commit()

        assert users[0].all_rooms() == [rooms[0]]
        assert users[1].all_rooms() == [rooms[0], rooms[1]]
        assert users[2].all_rooms() == [rooms[0]]

        # Check adding a third user to a private room
        await rooms[1].add_participant(session, users[0])
        session.commit()
        assert rooms[1].participants == [users[0]]

        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            await rooms[1].add_participant(session, users[0])
            session.commit()
        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "Participant is already in the room"


        # check adding the same user twice
        exc_info = None
        with pytest.raises(RoomValidationException) as e:
            exc_info = e
            print("users 2 id: ", users[2].id)
            await rooms[1].add_participant(session, users[2])
            session.commit()
        assert exc_info
        assert exc_info.value
        assert exc_info.value.args[0] == "Room is private"

    @pytest.mark.asyncio
    async def test_is_user_in_room(
        self, session: Session, users: list[User], rooms: list[Room]
    ):
        assert await rooms[1].is_user_in_room(session, users[1]) 
        assert not await rooms[1].is_user_in_room(session, users[0]) 
        assert not await rooms[1].is_user_in_room(session, users[2]) 

        await rooms[1].add_participant(session, users[0])
        session.commit()

        # check if participant only contains the added once
        assert rooms[1].participants == [users[0]]  

        assert await rooms[1].is_user_in_room(session, users[0]) 
        assert await rooms[1].is_user_in_room(session, users[1]) 
        assert not await rooms[1].is_user_in_room(session, users[2]) 


        # all public rooms should be accessible
        assert await rooms[0].is_user_in_room(session, users[0]) 
        assert await rooms[0].is_user_in_room(session, users[1]) 
        assert await rooms[0].is_user_in_room(session, users[2]) 

    @pytest.mark.asyncio
    async def test_room_expiry(
            self,
            session: Session,
            unexpired_rooms: list[Room],
            expired_rooms: list[Room],
            users: list[User]
    ):

        query = (
            select(Room)
            .where(
                or_(
                    Room.last_interacted > datetime.now() - timedelta(seconds=50),
                    Room.room_type == RoomType.PRIVATE
                )
            )
        )

        queried_rooms = session.exec(query).all()
        assert len(queried_rooms) == len(unexpired_rooms)

        for room in queried_rooms:
            assert room not in expired_rooms

    @pytest.mark.asyncio
    async def test_room_expiry_deletion(
            self,
            session: Session,
            unexpired_rooms: list[Room],
            expired_rooms: list[Room],
            users: list[User]
    ):

        expired_room_ids = [room.id for room in expired_rooms]
        delete_query = (
            delete(Room)
            .where(
                or_(
                    Room.last_interacted < datetime.now() - timedelta(seconds=50),
                    Room.room_type == RoomType.PRIVATE
                )
            )
        )

        session.exec(delete_query)
        session.commit()

        select_query = select(Room)
        queried_rooms = session.exec(select_query).all()
        session.commit()

        assert len(queried_rooms) == len(unexpired_rooms)

        for room in queried_rooms:
            assert room.id not in expired_room_ids 

    @pytest.mark.asyncio
    async def test_send_message(
            self,
            session: Session,
            users: list[User],
            rooms: list[Room],
            # messages: dict[str, list[Message]],
    ):
        assert users[0].id
        assert rooms[0].id
        consumer1 = rooms[0].kafka_consumer()

        messages = [
            Message(text="test msg 1", owner_id=users[0].id, room_id=rooms[0].id),
            Message(text="test msg 2", owner_id=users[0].id, room_id=rooms[0].id),
            Message(text="test msg 3", owner_id=users[0].id, room_id=rooms[0].id),
        ]
        rooms[0].messages.extend(messages)
        session.commit()
        session.refresh(rooms[0])

        sent_msg = await rooms[0].send_message(messages)
        assert sent_msg

        # consume message as all other users
        msg1 = consumer1.poll(10)

        if msg1 is None:
            print("no message")
            raise KafkaException("no message")
        elif msg1.error():
            print("error: ", msg1.error())
            raise KafkaException(msg1.error())
        else:
            msg1 = json.loads(msg1.value().decode('utf-8'))
            assert msg1["type"] == "text"
            assert msg1["message_id"] == sent_msg[0].id
            assert msg1["message_id"] != sent_msg[1].id
            assert msg1["message_id"] != sent_msg[2].id

        consumer1.close()

    @pytest.mark.asyncio
    async def test_message_stream(
        self,
        session: Session,
        users: list[User],
        rooms: list[Room],
    ):
        assert users[0].id and rooms[0].id
        messages = [
            Message(text="test msg 1", owner_id=users[0].id, room_id=rooms[0].id),
            Message(text="test msg 2", owner_id=users[0].id, room_id=rooms[0].id),
            Message(text="test msg 3", owner_id=users[0].id, room_id=rooms[0].id),
        ]

        rooms[0].messages.extend(messages)
        session.commit()
        session.refresh(rooms[0])

        producer = rooms[0].kafka_producer()

        for message in messages:
            producer.produce(
                topic=rooms[0].kafka_topic_name(),
                value=json.dumps({
                    "type": "text",
                    "message_id": message.id
                })
            )

        new_messages = rooms[0].message_stream()

        msg1 = next(new_messages)
        assert msg1
        assert msg1.id == messages[0].id 

        msg2 = next(new_messages)
        assert msg2
        assert msg2.id == messages[1].id

        msg3 = next(new_messages)
        assert msg3
        assert msg3.id == messages[2].id

    # @pytest.mark.asyncio
    # async def test_message_stream_with_multiple_consumers(
    #     self,
    #     session: Session,
    #     users: list[User],
    #     rooms: list[Room],
    # ):
    #     assert users[0].id and rooms[0].id
    #     messages = [
    #         Message(text="test msg 1", owner_id=users[0].id, room_id=rooms[0].id),
    #         Message(text="test msg 2", owner_id=users[0].id, room_id=rooms[0].id),
    #         Message(text="test msg 3", owner_id=users[0].id, room_id=rooms[0].id),
    #     ]
    #     rooms[0].messages.extend(messages)
    #     session.commit()
    #     session.refresh(rooms[0])
    #
    #     producer = rooms[0].kafka_producer()
    #     errors = []
    #
    #     for message in messages:
    #         producer.produce(
    #             topic=rooms[0].kafka_topic_name(),
    #             value=json.dumps({
    #                 "type": "text",
    #                 "message_id": message.id
    #             })
    #         )
    #
    #         producer.flush()
    #
    #     def collect_messages(room: Room):
    #         print("collecting messages with a thread")
    #         gen = room.message_stream()
    #
    #         for _ in range(len(messages)):
    #             msg = next(gen)
    #             try:
    #                 assert msg
    #                 assert msg.id in [m.id for m in messages]
    #             except Exception as e:
    #                 errors.append(e)
    #
    #
    #     t1 = threading.Thread(target=collect_messages, args=(rooms[0],))
    #     t2 = threading.Thread(target=collect_messages, args=(rooms[0],))
    #
    #     t1.start()
    #     t2.start()
    #
    #     t1.join()
    #     t2.join()
    #
    #     if len(errors) > 0:
    #         print(errors)
    #
    #     assert len(errors) == 0


