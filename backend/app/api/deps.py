import base64
import hashlib
import hmac
import json
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import AgeGroup, User

SessionDep = Annotated[Session, Depends(get_session)]


# Token = podpisany profil (nick, avatar, wiek). Dzięki temu sesja przeżywa reset bazy i działa na każdej
# instancji funkcji na Vercelu — jeśli konta nie ma w bazie, odtwarzamy je z tokenu.
def _sig(payload: str) -> str:
    secret = (get_settings().session_secret or "sztafeta-dev").encode()
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()[:32]


def sign_token(nick: str, avatar: str, age_group: str) -> str:
    raw = json.dumps({"n": nick, "a": avatar, "g": age_group}, ensure_ascii=False, separators=(",", ":"))
    payload = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return f"{payload}.{_sig(payload)}"


def read_token(token: str) -> dict | None:
    payload, _, sig = token.partition(".")
    if not sig or not hmac.compare_digest(sig, _sig(payload)):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        AgeGroup(data["g"])
        return data
    except (ValueError, KeyError, TypeError):
        return None


def current_user(session: SessionDep, authorization: Annotated[str | None, Header()] = None) -> User:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Zaloguj się")
    user = session.exec(select(User).where(User.token == token)).first()
    if user:
        return user
    data = read_token(token)
    if not data:
        raise HTTPException(401, "Sesja wygasła — zaloguj się ponownie")
    user = session.exec(select(User).where(User.nick == data["n"])).first() or User(nick=data["n"])
    user.avatar, user.age_group, user.token = data["a"], AgeGroup(data["g"]), token
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


UserDep = Annotated[User, Depends(current_user)]
