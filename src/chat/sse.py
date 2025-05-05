from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio


router = APIRouter(prefix="/sse")


class SSEMessage(BaseModel):
    event: str
    data: dict


async def message_event_generator():
    for i in range(10):
        # Yield data in SSE format
        yield f"data: This is Message {i}\n\n"
        await asyncio.sleep(1)


@router.get("/stream")
async def message_stream():
    return StreamingResponse(message_event_generator(), media_type="text/event-stream")
