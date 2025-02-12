from datetime import datetime, timedelta
import os
from typing import Annotated, Any
import uuid
import dotenv
import httpx
from pydantic import BaseModel, Field, Json, ValidationError

dotenv.load_dotenv()


class KeyclockApiException(Exception):
    pass


class KeyclockUser(BaseModel):
    id: uuid.UUID
    username: str
    firstName: str
    lastName: str
    email: str
    created_timestamp: Annotated[int, Field(alias="createdTimestamp")]


class Keyclock:
    url = os.getenv("KEYCLOCK_URL")
    realm = os.getenv("KEYCLOCK_REALM")
    client_secret = os.getenv("KEYCLOCK_CLIENT_SECRET")
    client_id = os.getenv("KEYCLOCK_CLIENT_ID")
    token_url = f"{url}/realms/{realm}/protocol/openid-connect/token"
    _service_access_token = {}

    common_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": "AWSALBAPP-0=_remove_; AWSALBAPP-1=_remove_; AWSALBAPP-2=_remove_; AWSALBAPP-3=_remove_",
    }

    @property
    async def service_access_token(self):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        if self._service_access_token:
            if self._service_access_token["expires_in_dt"] > datetime.now():
                return self._service_access_token["access_token"]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url, headers=self.common_headers, data=payload
            )

            data = response.json()
            self._service_access_token = data.copy()
            self._service_access_token["expires_in_dt"] = datetime.now() + timedelta(
                seconds=data["expires_in"]
            )
            return data["access_token"]

    async def get_user(self, user_id: str) -> KeyclockUser:
        url = f"{self.url}/admin/realms/{self.realm}/users/{user_id}"

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url, headers={"Authorization": f"Bearer {await self.service_access_token}"}
            )

        if res.status_code == 200:
            user_dict = res.json()
            try:
                user = KeyclockUser.model_validate(user_dict)
                return user
            except ValidationError as e:
                raise KeyclockApiException(
                    "User validation error", e.errors(), user_dict
                )
        else:
            raise KeyclockApiException("User not found", res.json())

