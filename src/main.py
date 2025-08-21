import dotenv
import os

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import DEFAULT_UNIVERSAL_GROUP_EXPIRY
from .chat import socket, sse
from .models import SQLModel, engine, wait_for_postgres
from .tasks import remove_expired_rooms_once
from .routers import users, rooms
from axiom_py.logging import AxiomHandler
import axiom_py
import logging
from datetime import datetime

dotenv.load_dotenv()

# class AxiomFormatter(logging.Formatter):
#     def format(self, record):
#         # Extract relevant fields from Uvicorn access log
#         if record.name == "uvicorn.access" and record.args:
#             client = record.args[0]
#             method = record.args[1]
#             path = record.args[2]
#             http_version = record.args[3]
#             status_code = record.args[4]
#             timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
#             return f"{timestamp} - {client} - {method} {path} HTTP/{http_version} {status_code}"
#         # For other logs (e.g., uvicorn.error or custom logs), keep minimal format
#         timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
#         return f"{timestamp} - {record.levelname} - {record.getMessage()}"

def setup_axiom_logger():
    client = axiom_py.Client(os.getenv("AXIOM_TOKEN"))
    handler = AxiomHandler(client, os.getenv("AXIOM_DATASET", "mindplex-chat-app"))
    # handler.setFormatter()

    # Add to root for custom/app logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # Add to Uvicorn loggers for server and request logs
    logging.getLogger("uvicorn.error").addHandler(handler)
    logging.getLogger("uvicorn.access").addHandler(handler)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # start axiom
    setup_axiom_logger()

    # TODO: create proper db migrations. see https://alembic.sqlalchemy.org/en/latest/ 
    SQLModel.metadata.create_all(engine)
    wait_for_postgres()
    yield
    # SQLModel.metadata.drop_all(engine)

app = FastAPI(lifespan=lifespan)

logging.info("Axiom setup complelte!!!")

# routers
app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(socket.router)
app.include_router(sse.router)


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
