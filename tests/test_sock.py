from fastapi import WebSocketDisconnect, WebSocketException
from fastapi.testclient import TestClient
from sqlalchemy.sql.compiler import exc
from .fixtures import *


class TestConnectionManager:
    pass


class TestWebSocketEndpoint:
    def test_no_auth(self, client: TestClient, rooms_with_mindplex: list[Room]):
        endpoint = f"/ws/rooms/{rooms_with_mindplex[0].id}?token=invalid_token&username=test_user"
        # check if the room exists

        with client.websocket_connect(endpoint) as websocket:
            response = websocket.receive_json()
            print("response: ", response)
            print("response type: ", type(response))
            print("response keys: ", response.keys())

            assert response["success"] == False
            assert response["error"]["status_code"] == 401
            assert response["error"]["short_code"] == "unauthorized"

    def test_no_room(self, token: str, client: TestClient):
        endpoint = f"/ws/rooms/invalid_room_id?token={token}&username=dave"
        # check if the room exists

        with client.websocket_connect(endpoint) as websocket:
            response = websocket.receive_json()
            assert response["success"] == False
            assert response["error"]["status_code"] == 404
            assert response["error"]["short_code"] == "not_found"

    def test_with_room_not_member(
        self, token: str, client: TestClient, rooms_with_mindplex: list[Room]
    ):
        endpoint = f"/ws/rooms/{rooms_with_mindplex[2].id}?token={token}&username=dave"

        with client.websocket_connect(endpoint) as websocket:
            response = websocket.receive_json()
            assert response["success"] == False
            assert response["error"]["status_code"] == 403
            assert response["error"]["short_code"] == "not_in_room"

    def test_with_room_member(
        self, token: str, client: TestClient, rooms_with_mindplex: list[Room]
    ):
        endpoint = f"/ws/rooms/{rooms_with_mindplex[1].id}?token={token}&username=dave"

        with client.websocket_connect(endpoint) as websocket:
            response = websocket.receive_json()
            assert response["success"] == True
            assert response["message"]["type"] == "connected"

