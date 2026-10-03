"""Live updates przez polling (Vercel nie obsługuje WebSocketów).

Klient wysyła kursor z poprzedniej odpowiedzi; serwer zwraca zmiany od tego momentu.
Kursor bierzemy z zegara serwera PRZED zapytaniami i porównujemy `>=`, więc nic nie ginie
(duplikaty klient deduplikuje po id).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import SessionDep, UserDep
from app.api.dto import SegmentOut, StoryOut, segments_out, stories_out
from app.models import Segment, SegmentStatus, Story, now

router = APIRouter(prefix="/api", tags=["updates"])


class UpdatesOut(BaseModel):
    cursor: datetime
    stories: list[StoryOut]
    segments: list[SegmentOut]
    my_segments: list[SegmentOut]


@router.get("/updates", response_model=UpdatesOut)
def updates(session: SessionDep, user: UserDep, since: datetime | None = None):
    cursor = now()
    since = since or cursor - timedelta(seconds=30)

    stories = session.exec(select(Story).where(Story.updated_at >= since).order_by(Story.updated_at)).all()
    segs = session.exec(
        select(Segment)
        .where(Segment.updated_at >= since, Segment.status == SegmentStatus.approved)
        .order_by(Segment.position)
    ).all()
    mine = session.exec(select(Segment).where(Segment.updated_at >= since, Segment.author_id == user.id)).all()

    return UpdatesOut(
        cursor=cursor,
        stories=stories_out(session, list(stories), user.id),
        segments=segments_out(session, list(segs)),
        my_segments=segments_out(session, list(mine)),
    )

