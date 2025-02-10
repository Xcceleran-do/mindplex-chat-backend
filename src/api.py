from datetime import datetime, timedelta
import os
from typing import Any
import dotenv
import httpx
from pydantic import Json

dotenv.load_dotenv()


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
                print("Access Token 1: ", self._service_access_token["access_token"])
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
            print("Access Token 2: ", data["access_token"])
            return data["access_token"]

    def get_user(self, user_id: str) -> dict[Any, Any]:
        url = f"{self.url}/realms/{self.realm}/users/{user_id}"

        return httpx.get(
            url, headers={"Authorization": f"Bearer {self.service_access_token}"}
        ).json()
