from fastapi.testclient import TestClient
from ..fixtures import *
import asyncio


class TestWebsocketEndpoint:
    def test_no_auth(self, client: TestClient, rooms_with_mindplex: list[Room]):
        endpoint = f"/ws/rooms/{rooms_with_mindplex[0].id}?token=invalid_token&username=test_user"
        # check if the room exists

        with client.websocket_connect(endpoint) as websocket:
            response = websocket.receive_json()

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

    @pytest.mark.asyncio
    async def test_with_multiple_sockets(
        self, token: str, test_token1:str, client: TestClient, rooms: list[Room]
    ):

        endpoint1 = f"/ws/rooms/{rooms[0].id}?token={token}&username=dave"
        with client.websocket_connect(endpoint1) as websocket1:
            connection_response1 = websocket1.receive_json()
            print("connection_response1: ", connection_response1)
            assert connection_response1["success"] == True
            assert connection_response1["message"]["type"] == "connected"

            endpoint2 = f"/ws/rooms/{rooms[0].id}?token={test_token1}&username=test151"
            with client.websocket_connect(endpoint2) as websocket2:
                connection_response2 = websocket2.receive_json()
                assert connection_response2["success"] == True
                assert connection_response2["message"]["type"] == "connected"

                websocket1.send_json(
                    {
                        "type": "text",
                        "message": "hello world",
                    }
                )

                async def recieve_new_message(websocket):
                    msg = websocket.receive_json()
                    return msg

                t1 = asyncio.wait_for(recieve_new_message(websocket1), timeout=10)
                t2 = asyncio.wait_for(recieve_new_message(websocket2), timeout=10)
                msg1_receipt = await t2
                msg1_confirmation = await t1

                assert msg1_confirmation["success"] == True
                assert msg1_confirmation["message"]["type"] == "sent_confirmation"

                assert msg1_receipt["success"] == True
                assert msg1_receipt["message"]["type"] == "text"
                assert msg1_receipt["message"]["message"]["text"] == "hello world"





                # msg1_confirmation = websocket1.receive_json()
                # assert msg1_confirmation["success"] == True
                # assert msg1_confirmation["message"]["type"] == "sent_confirmation"
                #
                # msg1_receipt = websocket2.receive_json()
                # assert msg1_receipt["success"] == True
                # assert msg1_receipt["message"]["type"] == "text"
                # assert msg1_receipt["message"]["message"] == "hello world"



