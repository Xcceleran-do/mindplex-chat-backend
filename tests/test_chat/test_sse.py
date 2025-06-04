from ..fixtures import *
from fastapi.testclient import TestClient

class TestMessageStream:

    def test_message_stream(
        self,
        client: TestClient,
        token: str,
        rooms: list[Room]
    ):
        pass

    def test_without_room(self):
        pass

    def test_user_not_in_room(self):
        pass
