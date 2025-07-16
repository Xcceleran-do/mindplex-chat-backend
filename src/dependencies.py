from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, HTTPException, Header, Query
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models import User, engine
import jwt


# settings and constants
DEFAULT_UNIVERSAL_GROUP_EXPIRY = 10 * 60


@asynccontextmanager
async def get_session_contextmanager() -> AsyncSession:
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


async def get_user(authorization: str, session: AsyncSession, *args, **kwargs) -> User:
    """Given Authorization header as string, authenticates and returns the user.
    Creates the user if it doesn't exist.

    Raises:
        HTTPException: if the header is malformed
        HTTPException: if the jwt is invalid

    Returns:
        User: the authenticated user
    """

    JWT_KEY = "e47a9bb31d8f785b2dbf4f0cd79879ae01de30f5" 

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = authorization.split(" ")[1]  # Extract the actual token

    try:
        # Verify the JWT using the public key
        payload = jwt.decode(
            token,
            JWT_KEY,
            algorithms=["HS256"],  
            options={
                "verify_aud": False
            },
            leeway=10
        )

    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # remote_id = payload["data"]["user"]["id"]

    # get remote_id(username) from header instead of the token
    remote_id = kwargs.get("username")

    if remote_id is None:
        raise HTTPException(status_code=401, detail="Missing username header")

    # get or create the user
    user = await session.execute(select(User).where(User.remote_id == remote_id))
    user = user.scalars().first()

    if user is None:
        user = User(
            remote_id=remote_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def get_user_dep(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str, Header()],
    x_username: Annotated[str, Header()]
) -> User:
    return await get_user(authorization, session, username=x_username)


async def get_user_from_qp_dep(
    session: Annotated[AsyncSession, Depends(get_session)], token: Annotated[str, Query()], username: Annotated[str, Query()]
) -> User | str:
    try:
        authorization = f"Bearer {token}"
        return await get_user(authorization, session, username=username)
    except HTTPException as e:
        return str(e)


