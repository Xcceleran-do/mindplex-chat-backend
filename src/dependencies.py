from typing import Annotated
from fastapi import Depends, HTTPException, Header, Query
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session, select
from src.models import User, engine
import jwt


def get_session():
    with Session(engine) as session:
        yield session


def get_user(authorization: str, session: Session) -> User:
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

    username = payload["data"]["user"]["id"]

    # get or create the user
    user = session.exec(select(User).where(User.remote_id == username)).first()
    print("user from token: ", payload)

    if user is None:
        user = User(
            remote_id=username,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    return user


async def get_user_dep(
    session: Annotated[Session, Depends(get_session)],
    authorization: Annotated[str, Header()],
) -> User:
    return get_user(authorization, session)


async def get_user_from_qp_dep(
    session: Annotated[Session, Depends(get_session)], token: Annotated[str, Query()]
) -> User | str:
    try:
        authorization = f"Bearer {token}"
        return get_user(authorization, session)
    except HTTPException as e:
        return str(e)
