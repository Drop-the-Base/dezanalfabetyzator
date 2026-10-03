"""Obiekty odpowiedzi API (to, co widzi frontend)."""

from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from app.models import AIReview, Segment, SegmentStatus, Story, User


class UserOut(BaseModel):
    id: int
    nick: str
    avatar: str
    age_group: str


class AuthorOut(BaseModel):
    id: int | None
    nick: str
    avatar: str
    is_ai: bool


AI_AUTHOR = AuthorOut(id=None, nick="Narrator AI", avatar="ai", is_ai=True)


class SegmentOut(BaseModel):
    id: int
    story_id: int
    position: int
    text: str
    status: str
    comprehension_score: int | None
    author: AuthorOut
    created_at: datetime
    updated_at: datetime


class StoryOut(BaseModel):
    id: int
    title: str
    theme: str
    age_group: str
    segment_count: int
    authors: list[AuthorOut]
    last_author_id: int | None
    created_at: datetime
    updated_at: datetime


class StoryDetail(StoryOut):
    segments: list[SegmentOut]


class ReviewOut(BaseModel):
    id: int
    segment_id: int
    kind: str
    verdict: str
    score: int | None
    reason: str
    evidence: str
    strengths: str
    categories: list[str]
    model: str
    created_at: datetime


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, nick=u.nick, avatar=u.avatar, age_group=u.age_group)


def author_out(u: User | None) -> AuthorOut:
    if u is None:
        return AI_AUTHOR
    return AuthorOut(id=u.id, nick=u.nick, avatar=u.avatar, is_ai=False)


def review_out(r: AIReview) -> ReviewOut:
    return ReviewOut(
        id=r.id, segment_id=r.segment_id, kind=r.kind, verdict=r.verdict, score=r.score, reason=r.reason,
        evidence=r.evidence, strengths=r.strengths,
        categories=[c for c in r.categories.split(",") if c], model=r.model, created_at=r.created_at,
    )


def _users(session: Session, ids: set[int]) -> dict[int, User]:
    if not ids:
        return {}
    return {u.id: u for u in session.exec(select(User).where(col(User.id).in_(ids))).all()}


def segments_out(session: Session, segs: list[Segment]) -> list[SegmentOut]:
    users = _users(session, {s.author_id for s in segs if s.author_id})
    return [
        SegmentOut(
            id=s.id, story_id=s.story_id, position=s.position, text=s.text, status=s.status,
            comprehension_score=s.comprehension_score,
            author=author_out(users.get(s.author_id) if s.author_id else None),
            created_at=s.created_at, updated_at=s.updated_at,
        )
        for s in segs
    ]


def stories_out(session: Session, stories: list[Story]) -> list[StoryOut]:
    if not stories:
        return []
    ids = [s.id for s in stories]
    approved = session.exec(
        select(Segment)
        .where(col(Segment.story_id).in_(ids), Segment.status == SegmentStatus.approved)
        .order_by(Segment.position)
    ).all()
    by_story: dict[int, list[Segment]] = {i: [] for i in ids}
    for seg in approved:
        by_story[seg.story_id].append(seg)
    users = _users(session, {s.author_id for s in approved if s.author_id})
    out = []
    for st in stories:
        segs = by_story[st.id]
        seen: dict[int | None, AuthorOut] = {}
        for seg in segs:
            seen.setdefault(seg.author_id, author_out(users.get(seg.author_id) if seg.author_id else None))
        out.append(
            StoryOut(
                id=st.id, title=st.title, theme=st.theme, age_group=st.age_group, segment_count=len(segs),
                authors=list(seen.values()), last_author_id=segs[-1].author_id if segs else None,
                created_at=st.created_at, updated_at=st.updated_at,
            )
        )
    return out


def next_position(session: Session, story_id: int) -> int:
    n = session.exec(select(func.max(Segment.position)).where(Segment.story_id == story_id)).one()
    return (n or 0) + 1
