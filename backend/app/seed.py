"""Dane demo. `uv run python -m app.seed` (idempotentne) lub `--reset` (czyści bazę).

Zestaw historii: app/demo_data.py. Ten sam reset robi `POST /api/admin/reset` (tryb jury, PIN z RESET_PIN).
Bez wywołań LLM — działa tak samo z Groq i z mockiem.
"""

import sys
from datetime import timedelta

from sqlalchemy import Engine, text
from sqlmodel import Session, SQLModel, select

from app.api.likes import demo_likes
from app.db import engine, init_db
from app.demo_data import DEMO_STORIES, DEMO_USERS, LIKED_STORIES
from app.models import AIReview, Like, ReviewKind, Segment, SegmentStatus, Story, User, now


def reset_db(bind: Engine) -> None:
    """Usuwa i zakłada od nowa wszystkie tabele (SQLite i Postgres)."""
    from app import models  # noqa: F401  (rejestracja tabel)

    if bind.dialect.name == "postgresql":
        # CASCADE: na wypadek tabel/kluczy obcych spoza bieżącego modelu (np. ze starszej wersji aplikacji).
        with bind.begin() as conn:
            for t in reversed(SQLModel.metadata.sorted_tables):
                conn.execute(text(f'DROP TABLE IF EXISTS "{t.name}" CASCADE'))
    SQLModel.metadata.drop_all(bind)  # kolejność wg kluczy obcych; na Postgresie sprząta też typy ENUM
    SQLModel.metadata.create_all(bind)


def seed_demo(s: Session) -> dict[str, int]:
    """Wstawia zestaw demo do pustej bazy. Zwraca liczniki. Commit robi wywołujący (demo_likes też commituje)."""
    t0 = now()
    users: dict[str, User] = {}
    for nick, (avatar, age) in DEMO_USERS.items():
        u = s.exec(select(User).where(User.nick == nick)).first() or User(nick=nick, avatar=avatar, age_group=age)
        s.add(u)
        users[nick] = u
    s.flush()

    stories: dict[str, Story] = {}
    segments: dict[tuple[str, int], Segment] = {}  # (tytuł, pozycja) → fragment — dla hooków poniżej
    reviews = 0
    for demo in DEMO_STORIES:
        n = len(demo.segments)
        updated = t0 - timedelta(minutes=demo.minutes_ago)
        at = [updated - timedelta(minutes=4 * (n - i)) for i in range(1, n + 1)]  # rosnąco, ostatni = updated
        st = Story(title=demo.title, theme=demo.theme, age_group=demo.age_group, created_at=at[0], updated_at=updated)
        s.add(st)
        s.flush()
        stories[demo.title] = st
        for pos, d in enumerate(demo.segments, 1):
            seg = Segment(
                story_id=st.id, author_id=users[d.author].id if d.author else None, position=pos, text=d.text,
                status=SegmentStatus.approved if d.approved else SegmentStatus.rejected,
                comprehension_score=d.review.score if d.review else None,
                created_at=at[pos - 1], updated_at=at[pos - 1],
            )
            s.add(seg)
            s.flush()
            segments[(demo.title, pos)] = seg
            mod = d.rejected_by
            s.add(AIReview(
                segment_id=seg.id, kind=ReviewKind.moderation, verdict="reject" if mod else "ok",
                reason=mod.reason if mod else "", categories=mod.categories if mod else "",
                model=mod.model if mod else "seed", created_at=at[pos - 1],
            ))
            reviews += 1
            if d.review:
                r = d.review
                s.add(AIReview(
                    segment_id=seg.id, kind=ReviewKind.comprehension, verdict=r.verdict, score=r.score,
                    reason=r.reason, evidence=r.evidence, strengths=r.strengths, model="seed",
                    created_at=at[pos - 1],
                ))
                reviews += 1

    counts = {
        "users": len(users),
        "stories": len(stories),
        "segments": sum(1 for x in segments.values() if x.status == SegmentStatus.approved),
        "rejected": sum(1 for x in segments.values() if x.status == SegmentStatus.rejected),
        "reviews": reviews,
    }

    # Polubienia (#31): „Na topie” od razu pełne. Kolejność = od najbardziej lubianej. Bez „Smoka” —
    # ta historia ma zostać w stanie startowym dla scenariusza z docs/DEMO.md.
    s.flush()
    demo_likes(s, {t: stories[t].id for t in LIKED_STORIES}, [u.id for u in users.values()])
    counts["likes"] = len(s.exec(select(Like)).all())

    # HOOK (poprawki, #32): gdy powstanie model poprawek, dodaj tu przykładowe zgłoszenia, np.
    #   counts["corrections"] = demo_corrections(s, users, stories, segments)
    # (segments: (tytuł, pozycja) → Segment; zaakceptowana + odrzucona poprawka z oceną AI).

    s.flush()
    return counts


def reset_and_seed(bind: Engine = engine) -> dict[str, int]:
    """Pełny reset bazy + dane demo (CLI `--reset` i POST /api/admin/reset)."""
    reset_db(bind)
    with Session(bind) as s:
        counts = seed_demo(s)
        s.commit()
    return counts


def seed(reset: bool = False) -> None:
    if reset:
        counts = reset_and_seed(engine)
        print(f"Seed: baza wyczyszczona, dane demo gotowe: {counts}")
        return
    init_db()
    with Session(engine) as s:
        if s.exec(select(Story)).first():
            print("Seed: dane już są — pomijam (użyj --reset).")
            return
        counts = seed_demo(s)
        s.commit()
    print(f"Seed: gotowe: {counts}")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
