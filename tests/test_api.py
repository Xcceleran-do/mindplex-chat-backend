from datetime import datetime

import jwt
from socketio.pubsub_manager import uuid
from src.api import Keyclock, KeyclockUser
import pytest
import logging
import os
import dotenv
from .fixtures import *

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

JWT_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAr+gOQGmyRCXO7UWGT9ub
Pap1jn+HFDk6i7RGXNQQagpan0OvDmo26IpT/fL9QfUpIvz+TaWRw+n171oduqK0
Qksv/hjHVYnHB+EcZ6TlyebTk1wCXxDTs0XLH2ugbSJtnhida/JBToeMzcArfPbU
ag6ZqBjNQqQXXe+gUvG8Ln0U9ZLfclz9NDqebdcHeVnQ+L4mOJiXHz5CHOcfPRhW
YI+rXIDC1zylWeQV0Dxcd0JThaVWnpiJA+ciBZzs9Hnf9zlaw63mS4sRBGGbjonx
tVe8eFWj9KDa7XbeQf6bG5T0Vfh8hLcwtg8jgkE+6IrrVR3HHHHEC/9JyoBsIrcZ
bwIDAQAB
-----END PUBLIC KEY-----
"""



class TestKeyClock:
    @pytest.mark.asyncio
    async def test_service_access_token(self):
        keyclock = Keyclock()
        sat = await keyclock.service_access_token
        sat_payload = jwt.decode(
            sat,
            JWT_KEY,
            algorithms=["RS256"],  # Ensure this matches the algorithm in the JWT header
            options={
                "verify_aud": False
            },  # Disable audience verification for this example
        )
        assert sat_payload["sub"] == "b335b5da-fd26-4407-b0cf-98213406d909"

        # Run again to check if the token is cached
        sat2 = await keyclock.service_access_token
        sat2_payload = jwt.decode(
            sat2,
            JWT_KEY,
            algorithms=["RS256"],  # Ensure this matches the algorithm in the JWT header
            options={
                "verify_aud": False
            },  # Disable audience verification for this example
        )

        assert sat2_payload["sub"] == "b335b5da-fd26-4407-b0cf-98213406d909"
        assert sat2_payload["exp"] == sat_payload["exp"]

    @pytest.mark.asyncio
    async def test_get_user(self, keyclock_users):
        kc = Keyclock()
        user1: KeyclockUser = keyclock_users["dave"]

        user_from_kc: KeyclockUser = await kc.get_user(
            "d11ddcca-4164-4078-b714-c8e8a37b3b22"
        )

        assert user_from_kc.id == user1.id
