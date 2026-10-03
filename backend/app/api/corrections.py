"""Poprawki: dziecko wskazuje niespójność w cudzym fragmencie i proponuje zmianę; AI ocenia.

Pipeline: walidacja → moderacja propozycji (lista słów + LLM) → werdykt LLM (prompt `correction.md`)
→ przy akceptacji podmiana tekstu fragmentu. Awaria LLM = bezpieczne odrzucenie („spróbuj za chwilę”),
nigdy automatyczna akceptacja. Każda decyzja (z surowym JSON-em) zostaje w tabeli `Correction`.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app.ai import services as ai
from app.ai.provider import LLMError
from app.api.deps import SessionDep, UserDep
from app.api.dto import AuthorOut, SegmentOut, author_out, segments_out
from app.models import Correction, CorrectionStatus, Segment, SegmentStatus, Story, User, now

router = APIRouter(prefix="/api", tags=["corrections"])

MAX_PROPOSED = 600
FALLBACK_FEEDBACK = "Nie udało mi się teraz sprawdzić Twojej poprawki. Spróbuj za chwilę!"


class NewCorrection(BaseModel):
    original: str = Field(min_length=1, max_length=1200)
    proposed: str = Field(min_length=1, max_length=MAX_PROPOSED)
    reason: str = Field(default="", max_length=300)


class CorrectionOut(BaseModel):
    id: int
    segment_id: int
    story_id: int
    story_title: str
    author: AuthorOut  # kto zaproponował
    segment_author: AuthorOut  # czyj fragment poprawiano
    original: str
    proposed: str
    reason: str
    status: str
    ai_feedback: str
    evidence: str
    model: str
    created_at: datetime


class CorrectionResult(BaseModel):
    correction: CorrectionOut
    segment: SegmentOut  # po ewentualnej podmianie tekstu
    blocked_by_moderation: bool = False


class ToFixOut(BaseModel):
    story_id: int
    story_title: str
    segment: SegmentOut


def corrections_out(session: Session, items: list[Correction]) -> list[CorrectionOut]:
    if not items:
        return []
    segs = {s.id: s for s in session.exec(select(Segment).where(col(Segment.id).in_({c.segment_id for c in items})))}
    stories = {s.id: s for s in session.exec(select(Story).where(col(Story.id).in_({c.story_id for c in items})))}
    user_ids = {c.author_id for c in items if c.author_id} | {s.author_id for s in segs.values() if s.author_id}
    users = {u.id: u for u in session.exec(select(User).where(col(User.id).in_(user_ids)))} if user_ids else {}
    out = []
    for c in items:
        seg = segs.get(c.segment_id)
        seg_author = seg.author_id if seg else None
        out.append(
            CorrectionOut(
                id=c.id, segment_id=c.segment_id, story_id=c.story_id,
                story_title=stories[c.story_id].title if c.story_id in stories else "",
                author=author_out(users.get(c.author_id) if c.author_id else None),
                segment_author=author_out(users.get(seg_author) if seg_author else None),
                original=c.original, proposed=c.proposed, reason=c.reason, status=c.status,
                ai_feedback=c.ai_feedback, evidence=c.evidence, model=c.model, created_at=c.created_at,
            )
        )
    return out


def _previous_text(session: Session, seg: Segment) -> str:
    segs = session.exec(
        select(Segment)
        .where(
            Segment.story_id == seg.story_id,
            Segment.status == SegmentStatus.approved,
            Segment.position < seg.position,
        )
        .order_by(Segment.position)
    ).all()
    return "\n\n".join(s.text for s in segs)


def _apply(session: Session, seg: Segment, original: str, proposed: str) -> None:
    """Podmienia pierwsze wystąpienie i podbija updated_at — polling (/api/updates) to zauważy."""
    seg.text = seg.text.replace(original, proposed, 1)
    seg.updated_at = now()
    session.add(seg)
    story = session.get(Story, seg.story_id)
    if story:
        story.updated_at = seg.updated_at
        session.add(story)


def _get_segment(session: Session, segment_id: int) -> Segment:
    seg = session.get(Segment, segment_id)
    if not seg or seg.status != SegmentStatus.approved:
        raise HTTPException(404, "Nie ma takiego fragmentu")
    return seg


@router.post("/segments/{segment_id}/corrections", response_model=CorrectionResult)
def propose_correction(segment_id: int, body: NewCorrection, session: SessionDep, user: UserDep):
    seg = _get_segment(session, segment_id)
    if seg.author_id == user.id:
        raise HTTPException(403, "To Twój fragment — poprawiamy tylko cudze teksty.")
    original, proposed, reason = body.original, body.proposed.strip(), body.reason.strip()
    if not original.strip() or original not in seg.text:
        raise HTTPException(422, "Nie mogę znaleźć zaznaczonego kawałka w tym fragmencie. Zaznacz go jeszcze raz.")
    if not proposed or proposed == original.strip():
        raise HTTPException(422, "Twoja wersja jest taka sama jak oryginał — zmień coś!")

    corr = Correction(
        segment_id=seg.id, story_id=seg.story_id, author_id=user.id,
        original=original, proposed=proposed, reason=reason,
    )
    story = session.get(Story, seg.story_id)
    age = story.age_group if story else user.age_group

    mod, source = ai.moderate(f"{proposed}\n\n{reason}".strip(), user.age_group)
    blocked = mod.verdict != "ok"
    if blocked:
        corr.status = CorrectionStatus.rejected
        corr.ai_feedback = mod.reason_for_kid or FALLBACK_FEEDBACK
        corr.model = source
        corr.raw_json = mod.model_dump_json()
    else:
        try:
            j = ai.judge_correction(_previous_text(session, seg), seg.text, original, proposed, reason, age)
            corr.status = CorrectionStatus.accepted if j.verdict == "accepted" else CorrectionStatus.rejected
            corr.ai_feedback = j.feedback_for_kid
            corr.evidence = j.evidence
            corr.model = ai.provider_name()
            corr.raw_json = j.model_dump_json()
        except LLMError as e:
            corr.status = CorrectionStatus.rejected
            corr.ai_feedback = FALLBACK_FEEDBACK
            corr.model = "fallback"
            corr.raw_json = json.dumps({"error": str(e)[:300]}, ensure_ascii=False)

    if corr.status == CorrectionStatus.accepted:
        _apply(session, seg, original, proposed)
    session.add(corr)
    session.commit()
    session.refresh(corr)
    session.refresh(seg)
    return CorrectionResult(
        correction=corrections_out(session, [corr])[0],
        segment=segments_out(session, [seg])[0],
        blocked_by_moderation=blocked,
    )


@router.get("/corrections", response_model=list[CorrectionOut])
def recent_corrections(session: SessionDep, user: UserDep, limit: int = 30):
    q = select(Correction).order_by(col(Correction.created_at).desc()).limit(min(max(limit, 1), 100))
    return corrections_out(session, list(session.exec(q).all()))


@router.get("/corrections/to-fix", response_model=list[ToFixOut])
def to_fix(session: SessionDep, user: UserDep, limit: int = 20):
    """Cudze fragmenty zrozumiane „częściowo” (40–79), jeszcze bez zaakceptowanej poprawki."""
    fixed = select(Correction.segment_id).where(Correction.status == CorrectionStatus.accepted)
    segs = list(
        session.exec(
            select(Segment)
            .where(
                Segment.status == SegmentStatus.approved,
                col(Segment.comprehension_score).between(40, 79),
                col(Segment.author_id).is_not(None),
                Segment.author_id != user.id,
                col(Segment.id).not_in(fixed),
            )
            .order_by(col(Segment.updated_at).desc())
            .limit(min(max(limit, 1), 50))
        ).all()
    )
    titles = {s.id: s.title for s in session.exec(select(Story).where(col(Story.id).in_({x.story_id for x in segs})))}
    return [
        ToFixOut(story_id=s.story_id, story_title=titles.get(s.story_id, ""), segment=o)
        for s, o in zip(segs, segments_out(session, segs), strict=True)
    ]


@router.get("/segments/{segment_id}/corrections", response_model=list[CorrectionOut])
def segment_corrections(segment_id: int, session: SessionDep, user: UserDep):
    if not session.get(Segment, segment_id):
        raise HTTPException(404, "Nie ma takiego fragmentu")
    q = select(Correction).where(Correction.segment_id == segment_id).order_by(col(Correction.created_at).desc())
    return corrections_out(session, list(session.exec(q).all()))


@router.get("/stories/{story_id}/corrections", response_model=list[CorrectionOut])
def story_corrections(story_id: int, session: SessionDep, user: UserDep):
    """Wszystkie poprawki w historii — frontend z nich wylicza znaczek „poprawione”."""
    q = select(Correction).where(Correction.story_id == story_id).order_by(col(Correction.created_at).desc())
    return corrections_out(session, list(session.exec(q).all()))


# --- Dane demo (bez wywołań LLM) ---


@dataclass
class DemoCorrection:
    """Gotowa, „już oceniona” poprawka do danych demo. `original` musi być dosłownie w tekście fragmentu."""

    segment: Segment
    author: User
    original: str
    proposed: str
    accepted: bool
    feedback: str
    evidence: str = ""
    reason: str = ""


def demo_corrections(session: Session, items: Iterable[DemoCorrection], commit: bool = True) -> list[Correction]:
    """Wstawia poprawki demo bez LLM. Zaakceptowane od razu podmieniają tekst fragmentu.

    Pozycje, których `original` nie ma w tekście fragmentu (albo autor = autor fragmentu), są pomijane.
    Przykład (seed.py):
        demo_corrections(session, [
            DemoCorrection(seg, kuba, "Fafik był niebieski", "Fafik był zielony", True,
                           "Brawo! Na początku smok był zielony.", evidence="Fafik był duży i zielony"),
        ])
    """
    created = []
    for it in items:
        seg = it.segment
        if seg.id is None or it.original not in seg.text or seg.author_id == it.author.id:
            continue
        corr = Correction(
            segment_id=seg.id, story_id=seg.story_id, author_id=it.author.id,
            original=it.original, proposed=it.proposed, reason=it.reason,
            status=CorrectionStatus.accepted if it.accepted else CorrectionStatus.rejected,
            ai_feedback=it.feedback, evidence=it.evidence, model="demo",
            raw_json=json.dumps(
                {"verdict": "accepted" if it.accepted else "rejected", "feedback_for_kid": it.feedback,
                 "evidence": it.evidence},
                ensure_ascii=False,
            ),
        )
        if it.accepted:
            _apply(session, seg, it.original, it.proposed)
        session.add(corr)
        created.append(corr)
    if commit:
        session.commit()
        for c in created:
            session.refresh(c)
    else:
        session.flush()
    return created
