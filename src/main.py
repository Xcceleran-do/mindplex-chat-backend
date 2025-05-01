import dotenv
import os

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from confluent_kafka import Producer, Consumer, KafkaException, KafkaError

from .dependencies import DEFAULT_UNIVERSAL_GROUP_EXPIRY
from . import socket
from .models import SQLModel, engine
from .tasks import remove_expired_rooms_once
from .routers import users, rooms


dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # TODO: create proper db migrations. see https://alembic.sqlalchemy.org/en/latest/ 
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)


# routers
app.include_router(socket.router)
app.include_router(users.router)
app.include_router(rooms.router)


# middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def remove_expired_rooms(request, call_next):
    await remove_expired_rooms_once(DEFAULT_UNIVERSAL_GROUP_EXPIRY)
    response = await call_next(request)
    return response



# test kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = "chatroom-general-1"

producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

@app.post("/send")
async def send_message(message: str):
    producer.produce(TOPIC, message.encode('utf-8'))
    producer.flush()
    return {"status": "message sent"}


@app.get("/consume")
async def consume_messages():
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'fastapi-group',
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe([TOPIC])

    messages = []
    try:
        for _ in range(5):
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    return {"messages": "no room available"}
                raise KafkaException(msg.error())
            messages.append(msg.value().decode('utf-8'))
    finally:
        consumer.close()

    return {"messages": messages}


