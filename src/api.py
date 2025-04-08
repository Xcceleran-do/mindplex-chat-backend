from datetime import datetime, timedelta
import os
from typing import Annotated, Any
import uuid
import dotenv
import httpx
from pydantic import BaseModel, Field, Json, ValidationError

dotenv.load_dotenv()


class MindplexApiException(Exception):
    pass

"""
    {
        "user_id": 13,
        "username": "esubalewA",
        "first_name": "Esubalew",
        "last_name": "Amenu",
        "theme": "light",
        "avatar_url": "https://secure.gravatar.com/avatar/5e9ebd86529dcac05164aacedf030ac7?s=96&d=mm&r=g",
        "mpxr": 13.26679,
        "is_following": false,
        "is_friends": false,
        "date_of_birth": "",
        "age": 27,
        "gender": "Other",
        "education": {
            "id": "37",
            "educational_background": "Master\\&#039;s degree                                                "
        },
        "interest": [],
        "social_media": [
            "https://twitter.com/EsubalewA"
        ],
        "biography": "lkdsjkjsdf",
        "followings": 3,
        "followers": 4,
        "friends": 0
    }
"""

class MindplexUser(BaseModel):
    """Mindplex data necessary for the chat app"""
    username: str
    first_name: str
    last_name: str
    avatar_url: str


class Mindplex:
    url = os.getenv("MINDPLEX_URL")

    async def get_user(self, username: str) -> MindplexUser:
        url = f"{self.url}/wp/v2/users/profile/{username}"

        async with httpx.AsyncClient() as client:
            res = await client.get(url)

        if res.status_code == 200:
            user_dict = res.json()
            try:
                user = MindplexUser.model_validate(user_dict)
                return user
            except ValidationError as e:
                raise MindplexApiException(
                    "User validation error", e.errors(), user_dict
                )
        else:
            raise MindplexApiException("User not found", res.json())

    async def get_user_id(self, user: MindplexUser | str) -> str:

        if type(user) is str:
            user = await self.get_user(user)

        assert type(user) is MindplexUser
        return user.username




