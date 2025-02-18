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

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = authorization.split(" ")[1]  # Extract the actual token

    try:
        # Verify the JWT using the public key
        payload = jwt.decode(
            token,
            JWT_KEY,
            algorithms=["RS256"],  
            options={
                "verify_aud": False
            },
        )

    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    # get or create the user
    user = session.exec(select(User).where(User.keyclock_id == payload["sub"])).first()

    if user is None:
        user = User(
            keyclock_id=payload["sub"],
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
