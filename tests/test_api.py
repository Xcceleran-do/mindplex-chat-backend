from datetime import datetime

import jwt
from src.api import Mindplex, MindplexUser
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



class TestMindplex:
    @pytest.mark.asyncio
    async def test_get_user(self, mindplex_users):
        mpx = Mindplex()
        user1: MindplexUser = mindplex_users["dave"]

        user_from_mpx: MindplexUser = await mpx.get_user("dave")

        assert user_from_mpx.username == user1.username
