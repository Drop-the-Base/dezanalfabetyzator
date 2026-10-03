"""Serduszka i zakładka „Na topie”.

Polubienie NIE zmienia `Story.updated_at` (to przestawiałoby kolejność na liście historii),
więc liczniki odświeżają się przy ponownym pobraniu (ekran „Na topie” odpytuje co kilka sekund).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from app.api.deps import SessionDep, UserDep
from app.api.dto import StoryOut, like_counts, stories_out
from app.models import Like, Segment, SegmentStatus, Story, now

router = APIRouter(prefix="/api", tags=["likes"])

TRENDING_LIMIT = 20
MIN_SEGMENTS = 2  # na topie tylko historie, które już naprawdę idą sztafetą


class LikeOut(BaseModel):
    like_count: int
    liked_by_me: bool


def _aware(dt: datetime) -> datetime:
    # SQLite zwraca daty bez strefy — zapisujemy je w UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def trending_score(likes: int, updated_at: datetime, at: datetime | None = None) -> float:
    """Polubienia z premią za świeżość: likes / (godziny + 2)^1.5."""
    hours = max(0.0, ((at or now()) - _aware(updated_at)).total_seconds() / 3600)
    return likes / (hours + 2) ** 1.5


def _like_state(session: Session, story_id: int, user_id: int) -> LikeOut:
    return LikeOut(
        like_count=like_counts(session, [story_id]).get(story_id, 0),
        liked_by_me=session.exec(select(Like).where(Like.story_id == story_id, Like.user_id == user_id)).first()
        is not None,
    )


def _ensure_story(session: Session, story_id: int) -> None:
    if not session.get(Story, story_id):
        raise HTTPException(404, "Nie ma takiej historii")


# Uwaga: ten router musi być dołączony PRZED `stories.router`, bo `/stories/trending` koliduje z `/stories/{id}`.
@router.get("/stories/trending", response_model=list[StoryOut])
def trending(session: SessionDep, user: UserDep):
    liked = session.exec(select(Like.story_id, func.count()).group_by(Like.story_id)).all()
    likes = {sid: n for sid, n in liked}
    if not likes:
        return []
    long_enough = set(
        session.exec(
            select(Segment.story_id)
            .where(col(Segment.story_id).in_(likes), Segment.status == SegmentStatus.approved)
            .group_by(Segment.story_id)
            .having(func.count() >= MIN_SEGMENTS)
        ).all()
    )
    if not long_enough:
        return []
    stories = session.exec(select(Story).where(col(Story.id).in_(long_enough))).all()
    at = now()
    ranked = sorted(
        stories,
        key=lambda s: (trending_score(likes[s.id], s.updated_at, at), _aware(s.updated_at)),
        reverse=True,
    )[:TRENDING_LIMIT]
    return stories_out(session, ranked, user.id)


@router.post("/stories/{story_id}/like", response_model=LikeOut)
def like(story_id: int, session: SessionDep, user: UserDep):
    _ensure_story(session, story_id)
    exists = session.exec(select(Like).where(Like.story_id == story_id, Like.user_id == user.id)).first()
    if not exists:
        session.add(Like(user_id=user.id, story_id=story_id))
        try:
            session.commit()
        except IntegrityError:  # podwójne kliknięcie — drugie żądanie przegrało wyścig, i dobrze
            session.rollback()
    return _like_state(session, story_id, user.id)


@router.delete("/stories/{story_id}/like", response_model=LikeOut)
def unlike(story_id: int, session: SessionDep, user: UserDep):
    _ensure_story(session, story_id)
    for row in session.exec(select(Like).where(Like.story_id == story_id, Like.user_id == user.id)).all():
        session.delete(row)
    session.commit()
    return _like_state(session, story_id, user.id)


def demo_likes(session: Session, story_ids_by_title: dict[str, int], user_ids: list[int]) -> None:
    """Dane demo: serduszka od użytkowników demo. Pierwsza historia dostaje najwięcej, kolejne coraz mniej.

    Idempotentne — istniejące polubienia są pomijane. Commituje sesję.
    """
    if not user_ids:
        return
    existing = set(session.exec(select(Like.user_id, Like.story_id)).all())
    for i, story_id in enumerate(story_ids_by_title.values()):
        for uid in user_ids[: max(1, len(user_ids) - i)]:
            if (uid, story_id) not in existing:
                session.add(Like(user_id=uid, story_id=story_id))
                existing.add((uid, story_id))
    session.commit()
