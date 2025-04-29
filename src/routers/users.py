from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from ..models import User, UserNotFoundException, Session
from ..dependencies import get_session, get_user_dep


router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/me", response_model=User)
async def get_me(user: Annotated[User, Depends(get_user_dep)]):
    return user


@router.get("/{username}", response_model=User)
async def get_users(
        session: Annotated[Session, Depends(get_session)],
        user: Annotated[User, Depends(get_user_dep)],
        username: str
):
    try:
        return await User.from_remote_or_db(username, session)
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")



