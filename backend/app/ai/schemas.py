from typing import Literal

from pydantic import BaseModel, Field


class ModerationResult(BaseModel):
    verdict: Literal["ok", "reject"]
    categories: list[str] = Field(default_factory=list)
    reason_for_kid: str = ""


class StoryStart(BaseModel):
    title: str
    text: str


class StoryContinuation(BaseModel):
    text: str


class ComprehensionResult(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: Literal["understood", "partially", "not_understood"]
    feedback_for_kid: str
    evidence: str = ""
    strengths: str = ""
