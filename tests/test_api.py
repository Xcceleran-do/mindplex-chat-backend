from src.api import Keyclock


class TestKeyClock:
    def test_service_access_token(self):
        keyclock = Keyclock()
        assert keyclock.service_access_token
