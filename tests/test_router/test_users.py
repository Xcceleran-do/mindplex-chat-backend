from typing import Any
from httpx import AsyncClient
from src.models import User
from ..fixtures import *

class TestGetUsers:
    
    @pytest.mark.asyncio
    async def test_auth(self, token: dict[str, Any], client: AsyncClient, users: list[User]):
        username = users[1].remote_id
        response = await client.get(
            f"/users/{username}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.status_code == 200

        
    @pytest.mark.asyncio
    async def test_no_auth(self, token: str, client: AsyncClient):
        response = await client.get("/users/dave")
        assert response.is_client_error
    
        
    @pytest.mark.asyncio
    async def test_get_user_by_valid_username(self, client: AsyncClient, token: str, users: list[User]):
        username = users[1].remote_id
        response = await client.get(
            f"/users/{username}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.status_code == 200
        assert response.json()["remote_id"] == username 

        
    @pytest.mark.asyncio
    async def test_get_user_by_invalid_username(self, client: AsyncClient, token: dict[str, Any]):
        response = await client.get(
            f"/users/invalid_usernameabc123",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        assert response.is_client_error
    
        
    @pytest.mark.asyncio
    async def test_get_user_by_mp_username(self, client: AsyncClient, token: dict[str, Any]):
        response = await client.get(
            f"/users/ivan2",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Username": "dave"
            }
        )
        data = response.json()
        assert response.status_code == 200
        assert data["remote_id"] == "ivan2" 


class TestGetMe:
    
    @pytest.mark.asyncio
    async def test_auth(self, token: dict[str, Any], client: AsyncClient):
        response = await client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )
        assert response.status_code == 200

        
    @pytest.mark.asyncio
    async def test_no_auth(self, client: AsyncClient):
        response = await client.get("/users/me")
        assert response.is_client_error

        
    @pytest.mark.asyncio
    async def test_valid_me(self, token: dict[str, Any], client: AsyncClient):
        response = await client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}", "X-Username": "dave"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["remote_id"] == "dave"


