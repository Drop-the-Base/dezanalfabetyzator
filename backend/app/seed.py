"""Dane demo. `uv run python -m app.seed` (idempotentne) lub `--reset` (czyści bazę)."""

import sys

from sqlmodel import Session, SQLModel, select

from app.ai.mock import STARTERS
from app.db import engine, init_db
from app.models import AgeGroup, AIReview, ReviewKind, Segment, SegmentStatus, Story, User

DEMO_USERS = [
    ("Zosia", "rabbit", AgeGroup.young),
    ("Kuba", "fox", AgeGroup.teen),
    ("Maja", "cat", AgeGroup.middle),
]


def seed(reset: bool = False) -> None:
    if reset:
        SQLModel.metadata.drop_all(engine)
    init_db()
    with Session(engine) as s:
        if s.exec(select(Story)).first():
            print("Seed: dane już są — pomijam (użyj --reset).")
            return
        users = {}
        for nick, avatar, age in DEMO_USERS:
            u = s.exec(select(User).where(User.nick == nick)).first() or User(nick=nick, avatar=avatar, age_group=age)
            s.add(u)
            users[nick] = u
        s.flush()

        for age, start in STARTERS.items():
            st = Story(title=start.title, theme="demo", age_group=age)
            s.add(st)
            s.flush()
            seg = Segment(story_id=st.id, author_id=None, position=1, text=start.text, status=SegmentStatus.approved)
            s.add(seg)
            s.flush()
            s.add(AIReview(segment_id=seg.id, kind=ReviewKind.moderation, verdict="ok", model="seed"))

        # Jedna historia już „w biegu”, żeby feed nie był pusty.
        maja_story = s.exec(select(Story).where(Story.age_group == AgeGroup.middle)).first()
        seg = Segment(
            story_id=maja_story.id, author_id=users["Maja"].id, position=2, status=SegmentStatus.approved,
            comprehension_score=88,
            text=(
                "Maja złapała Antka za rękę i razem wyjrzeli do sieni. Drzwi były uchylone, a na podłodze leżał "
                "mokry ślad buta — za duży jak na dziadka. Maja schowała mapę do kieszeni. Do zmroku zostało pół "
                "godziny, a młyn był dwadzieścia minut drogi stąd."
            ),
        )
        s.add(seg)
        s.flush()
        s.add(AIReview(
            segment_id=seg.id, kind=ReviewKind.comprehension, verdict="understood", score=88,
            reason="Super! Pamiętasz o ostrzeżeniu „Nie po zmroku” i o skrzypiących drzwiach.",
            evidence="Wtedy w sieni zaskrzypiały drzwi, chociaż dziadek wyjechał na cały dzień.",
            strengths="Świetnie budujesz napięcie.", model="seed",
        ))
        s.commit()
        print("Seed: gotowe.")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
