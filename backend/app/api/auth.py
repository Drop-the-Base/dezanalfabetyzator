"""Logowanie demo: nick + avatar + wiek. Bez haseł i danych osobowych."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select

from app.api.deps import SessionDep, UserDep
from app.api.dto import UserOut, user_out
from app.models import AgeGroup, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATARS = ["fox", "owl", "cat", "bear", "frog", "panda", "rabbit", "dragon"]


class DemoLogin(BaseModel):
    nick: str = Field(min_length=2, max_length=24)
    avatar: str
    age_group: AgeGroup


class LoginOut(BaseModel):
    token: str
    user: UserOut


@router.post("/demo", response_model=LoginOut)
def demo_login(body: DemoLogin, session: SessionDep):
    nick = body.nick.strip()
    if body.avatar not in AVATARS:
        raise HTTPException(422, "Nieznany avatar")
    user = session.exec(select(User).where(User.nick == nick)).first()
    if user:
        user.avatar, user.age_group = body.avatar, body.age_group
    else:
        user = User(nick=nick, avatar=body.avatar, age_group=body.age_group)
    session.add(user)
    session.commit()
    session.refresh(user)
    return LoginOut(token=user.token, user=user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: UserDep):
    return user_out(user)
