from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, room_id: str):
        self.active_connections[room_id].remove(websocket)

    async def send_message(self, message: str, room_id: str, websocket: WebSocket):
        """
        Send a message to a specific room excluding the sender.

        Args:
            message (str): the message to send
            room_id (str): the room to send the message to
            websocket (WebSocket): the websocket to exclude
        """
        for connection in self.active_connections[room_id]:
            if connection != websocket:
                await connection.send_text(message)
