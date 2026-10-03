from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]


def current_user(session: SessionDep, authorization: Annotated[str | None, Header()] = None) -> User:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Zaloguj się")
    user = session.exec(select(User).where(User.token == token)).first()
    if not user:
        raise HTTPException(401, "Sesja wygasła — zaloguj się ponownie")
    return user


UserDep = Annotated[User, Depends(current_user)]
