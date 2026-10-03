import secrets
from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC)


class AgeGroup(StrEnum):
    young = "7-10"
    middle = "11-14"
    teen = "15-18"


class SegmentStatus(StrEnum):
    approved = "approved"
    rejected = "rejected"


class ReviewKind(StrEnum):
    moderation = "moderation"
    comprehension = "comprehension"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nick: str = Field(index=True, max_length=24)
    avatar: str = Field(max_length=16)
    age_group: AgeGroup
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(24), index=True, unique=True)
    created_at: datetime = Field(default_factory=now)


class Story(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=120)
    theme: str = Field(default="", max_length=60)
    age_group: AgeGroup = Field(index=True)
    created_by: int | None = Field(default=None, foreign_key="user.id")  # None = AI
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, index=True)


class Segment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    story_id: int = Field(foreign_key="story.id", index=True)
    author_id: int | None = Field(default=None, foreign_key="user.id")  # None = AI
    position: int = 0
    text: str
    status: SegmentStatus = Field(default=SegmentStatus.approved, index=True)
    comprehension_score: int | None = None
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now, index=True)


class AIReview(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    segment_id: int = Field(foreign_key="segment.id", index=True)
    kind: ReviewKind
    verdict: str
    score: int | None = None
    reason: str = ""
    evidence: str = ""
    strengths: str = ""
    categories: str = ""
    model: str = ""
    raw_json: str = ""
    created_at: datetime = Field(default_factory=now, index=True)
