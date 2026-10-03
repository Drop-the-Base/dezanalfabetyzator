"""Historie i fragmenty + pipeline publikacji: moderacja → ocena zrozumienia → publikacja."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app.ai import services as ai
from app.ai.provider import LLMError
from app.api.deps import SessionDep, UserDep
from app.api.dto import (
    ReviewOut,
    SegmentOut,
    StoryDetail,
    StoryOut,
    next_position,
    review_out,
    segments_out,
    stories_out,
)
from app.models import AgeGroup, AIReview, ReviewKind, Segment, SegmentStatus, Story, User, now

router = APIRouter(prefix="/api", tags=["stories"])

THEMES = ["smoki", "kosmos", "detektyw", "piłka nożna", "gry komputerowe", "szkoła", "zwierzęta", "podróż w czasie"]
MAX_LEN = {AgeGroup.young: 400, AgeGroup.middle: 800, AgeGroup.teen: 1200}
MIN_LEN = 15


class NewStory(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    text: str = Field(min_length=MIN_LEN)
    theme: str = ""


class AIStory(BaseModel):
    theme: str = ""
    age_group: AgeGroup | None = None


class NewSegment(BaseModel):
    text: str = Field(min_length=1)


class ModerationOut(BaseModel):
    verdict: str
    reason: str
    categories: list[str]


class SubmitResult(BaseModel):
    segment: SegmentOut | None
    moderation: ModerationOut
    comprehension: ReviewOut | None
    ai_segment: SegmentOut | None = None  # ciąg dalszy narratora AI (historia się przeplata)
    story_id: int | None


def _check_len(text: str, user: User) -> str:
    text = text.strip()
    if len(text) < MIN_LEN:
        raise HTTPException(422, "Napisz trochę więcej — przynajmniej jedno pełne zdanie.")
    if len(text) > MAX_LEN[user.age_group]:
        raise HTTPException(422, f"Za długo! Maksymalnie {MAX_LEN[user.age_group]} znaków.")
    return text


def _review(session: Session, seg: Segment, kind: ReviewKind, **kw) -> AIReview:
    r = AIReview(segment_id=seg.id, kind=kind, **kw)
    session.add(r)
    return r


def _story_text(session: Session, story_id: int) -> str:
    segs = session.exec(
        select(Segment)
        .where(Segment.story_id == story_id, Segment.status == SegmentStatus.approved)
        .order_by(Segment.position)
    ).all()
    return "\n\n".join(s.text for s in segs)


def _ai_continue(session: Session, story: Story) -> Segment | None:
    """Po fragmencie dziecka narrator AI dopisuje swój — historia idzie AI → dziecko → AI → …"""
    try:
        text = ai.continue_story(_story_text(session, story.id), story.age_group)
    except LLMError:
        return None
    mod, source = ai.moderate(text, story.age_group)
    if mod.verdict != "ok" or len(text) < MIN_LEN:
        return None
    seg = Segment(story_id=story.id, author_id=None, position=next_position(session, story.id), text=text,
                  status=SegmentStatus.approved)
    session.add(seg)
    session.flush()
    _review(session, seg, ReviewKind.moderation, verdict="ok", model=source, raw_json=mod.model_dump_json())
    story.updated_at = now()
    session.add(story)
    session.commit()
    session.refresh(seg)
    return seg


def _get_story(session: Session, story_id: int) -> Story:
    story = session.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Nie ma takiej historii")
    return story


@router.get("/themes")
def themes():
    return THEMES


@router.get("/stories", response_model=list[StoryOut])
def list_stories(session: SessionDep, user: UserDep, age_group: AgeGroup | None = None):
    q = select(Story).order_by(col(Story.updated_at).desc()).limit(50)
    if age_group:
        q = q.where(Story.age_group == age_group)
    return stories_out(session, list(session.exec(q).all()), user.id)


@router.get("/stories/{story_id}", response_model=StoryDetail)
def get_story(story_id: int, session: SessionDep, user: UserDep):
    story = _get_story(session, story_id)
    segs = session.exec(
        select(Segment)
        .where(Segment.story_id == story_id, Segment.status == SegmentStatus.approved)
        .order_by(Segment.position)
    ).all()
    base = stories_out(session, [story], user.id)[0]
    return StoryDetail(**base.model_dump(), segments=segments_out(session, list(segs)))


@router.post("/stories", response_model=SubmitResult)
def create_story(body: NewStory, session: SessionDep, user: UserDep):
    text = _check_len(body.text, user)
    mod, source = ai.moderate(f"{body.title}\n\n{text}", user.age_group)
    mod_out = ModerationOut(verdict=mod.verdict, reason=mod.reason_for_kid, categories=mod.categories)
    if mod.verdict == "reject":
        return SubmitResult(segment=None, moderation=mod_out, comprehension=None, story_id=None)
    story = Story(title=body.title.strip(), theme=body.theme, age_group=user.age_group, created_by=user.id)
    session.add(story)
    session.flush()
    seg = Segment(story_id=story.id, author_id=user.id, position=1, text=text, status=_status(mod.verdict))
    session.add(seg)
    session.flush()
    _review(session, seg, ReviewKind.moderation, verdict=mod.verdict, reason=mod.reason_for_kid,
            categories=",".join(mod.categories), model=source, raw_json=mod.model_dump_json())
    session.commit()
    session.refresh(seg)
    ai_seg = _ai_continue(session, story) if seg.status == SegmentStatus.approved else None
    return SubmitResult(
        segment=segments_out(session, [seg])[0], moderation=mod_out, comprehension=None,
        ai_segment=segments_out(session, [ai_seg])[0] if ai_seg else None, story_id=story.id,
    )


@router.post("/stories/ai", response_model=StoryOut)
def create_ai_story(body: AIStory, session: SessionDep, user: UserDep):
    age = body.age_group or user.age_group
    try:
        start = ai.start_story(age, body.theme)
    except LLMError as e:
        raise HTTPException(503, "Narrator AI jest chwilowo zajęty. Spróbuj za moment.") from e
    mod, source = ai.moderate(f"{start.title}\n\n{start.text}", age)
    if mod.verdict != "ok":
        raise HTTPException(503, "Narrator AI napisał coś nie tak — spróbuj inny temat.")
    story = Story(title=start.title.strip()[:120], theme=body.theme, age_group=age, created_by=None)
    session.add(story)
    session.flush()
    seg = Segment(story_id=story.id, author_id=None, position=1, text=start.text.strip(),
                  status=SegmentStatus.approved)
    session.add(seg)
    session.flush()
    _review(session, seg, ReviewKind.moderation, verdict="ok", model=source, raw_json=mod.model_dump_json())
    session.commit()
    session.refresh(story)
    return stories_out(session, [story], user.id)[0]


def _status(verdict: str) -> SegmentStatus:
    return SegmentStatus.approved if verdict == "ok" else SegmentStatus.rejected


@router.post("/stories/{story_id}/segments", response_model=SubmitResult)
def add_segment(story_id: int, body: NewSegment, session: SessionDep, user: UserDep):
    story = _get_story(session, story_id)
    text = _check_len(body.text, user)

    # Sztafeta: między fragmentami AI piszą różne dzieci — nie ta sama osoba dwa razy z rzędu.
    last_human = session.exec(
        select(Segment)
        .where(
            Segment.story_id == story_id,
            Segment.status == SegmentStatus.approved,
            col(Segment.author_id).is_not(None),
        )
        .order_by(col(Segment.position).desc())
    ).first()
    if last_human and last_human.author_id == user.id:
        raise HTTPException(409, "Teraz kolej kogoś innego! Poczekaj, aż ktoś przejmie pałeczkę.")

    previous = _story_text(session, story_id)
    mod, source = ai.moderate(text, user.age_group)
    seg = Segment(
        story_id=story_id, author_id=user.id, position=next_position(session, story_id), text=text,
        status=_status(mod.verdict),
    )
    session.add(seg)
    session.flush()
    _review(session, seg, ReviewKind.moderation, verdict=mod.verdict, reason=mod.reason_for_kid,
            categories=",".join(mod.categories), model=source, raw_json=mod.model_dump_json())

    comp_review: AIReview | None = None
    if mod.verdict == "ok":
        # Ocena zrozumienia tylko doradza (pochwała + wskazówka) — nigdy nie blokuje. Blokuje wyłącznie
        # moderacja (treści obraźliwe/niestosowne). Mniej spójne fragmenty trafiają do „Do poprawienia”.
        # Awaria LLM też nie blokuje dzieci.
        try:
            comp = ai.assess_comprehension(previous, text, user.age_group)
            seg.comprehension_score = comp.score
            comp_review = _review(
                session, seg, ReviewKind.comprehension, verdict=comp.verdict, score=comp.score,
                reason=comp.feedback_for_kid, evidence=comp.evidence, strengths=comp.strengths,
                model=ai.provider_name(), raw_json=comp.model_dump_json(),
            )
        except LLMError:
            pass
        if seg.status == SegmentStatus.approved:
            story.updated_at = now()
            session.add(story)

    seg.updated_at = now()
    session.add(seg)
    session.commit()
    session.refresh(seg)
    if comp_review:
        session.refresh(comp_review)
    ai_seg = _ai_continue(session, story) if seg.status == SegmentStatus.approved else None
    return SubmitResult(
        segment=segments_out(session, [seg])[0],
        moderation=ModerationOut(verdict=mod.verdict, reason=mod.reason_for_kid, categories=mod.categories),
        comprehension=review_out(comp_review) if comp_review else None,
        ai_segment=segments_out(session, [ai_seg])[0] if ai_seg else None,
        story_id=story_id,
    )


@router.get("/segments/{segment_id}/reviews", response_model=list[ReviewOut])
def segment_reviews(segment_id: int, session: SessionDep, user: UserDep):
    seg = session.get(Segment, segment_id)
    if not seg:
        raise HTTPException(404, "Nie ma takiego fragmentu")
    rs = session.exec(select(AIReview).where(AIReview.segment_id == segment_id).order_by(AIReview.created_at)).all()
    return [review_out(r) for r in rs]
