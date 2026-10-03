import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.ai.mock import STARTERS
from app.config import get_settings
from app.db import get_session
from app.demo_data import DEMO_STORIES, check_dataset
from app.main import app
from app.models import AIReview, Correction, ReviewKind, Segment, SegmentStatus, Story

PIN = "2468"


@pytest.fixture
def engine():
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


@pytest.fixture
def client(engine):
    SQLModel.metadata.create_all(engine)

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def pin(monkeypatch):
    monkeypatch.setattr(get_settings(), "reset_pin", PIN)
    monkeypatch.setattr(get_settings(), "reset_requires_pin", True)
    return PIN


def login(client, nick, age="7-10", avatar="fox"):
    r = client.post("/api/auth/demo", json={"nick": nick, "avatar": avatar, "age_group": age})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_dataset_is_consistent():
    # cytaty dosłowne, sztafeta (nikt dwa razy z rzędu), limity długości, „Smok” w stanie startowym
    assert check_dataset() == []
    ages = {s.age_group for s in DEMO_STORIES}
    assert len(ages) == 3 and 6 <= len(DEMO_STORIES) <= 8


def test_reset_disabled_without_pin(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "reset_pin", "")
    monkeypatch.setattr(get_settings(), "reset_requires_pin", True)
    r = client.post("/api/admin/reset", headers={"X-Reset-Pin": ""})
    assert r.status_code == 403
    r = client.post("/api/admin/reset", headers={"X-Reset-Pin": "cokolwiek"})
    assert r.status_code == 403


def test_open_reset_for_jury_has_cooldown(client, monkeypatch, engine):
    """Domyślnie (tryb jury) reset bez PIN-u, ale nie częściej niż raz na RESET_COOLDOWN_S."""
    from app.api import admin

    monkeypatch.setattr(get_settings(), "reset_requires_pin", False)
    monkeypatch.setattr(admin, "_last_open_reset", 0.0)
    assert client.post("/api/admin/reset").status_code == 200
    with Session(engine) as s:
        assert s.exec(select(Story)).first() is not None
    assert client.post("/api/admin/reset").status_code == 429


def test_reset_wrong_pin(client, pin, engine):
    r = client.post("/api/admin/reset", headers={"X-Reset-Pin": "0000"})
    assert r.status_code == 403
    assert client.post("/api/admin/reset").status_code == 403  # brak nagłówka
    with Session(engine) as s:
        assert s.exec(select(Story)).first() is None  # nic nie ruszone


def test_reset_with_pin_seeds_demo(client, pin, engine):
    kid = login(client, "Ktoś")
    client.post("/api/stories", json={"title": "Do usunięcia", "text": "To jest historia, która zniknie po resecie."},
                headers=kid)

    r = client.post("/api/admin/reset", headers={"X-Reset-Pin": pin})
    assert r.status_code == 200, r.text
    counts = r.json()["counts"]
    assert counts["stories"] == len(DEMO_STORIES)
    assert counts["rejected"] >= 2 and counts["likes"] > 0

    jury = login(client, "Jury", "15-18", "owl")  # stary token przepadł razem z bazą
    stories = client.get("/api/stories", headers=jury).json()
    titles = {s["title"] for s in stories}
    assert "Do usunięcia" not in titles
    assert {s["age_group"] for s in stories} == {"7-10", "11-14", "15-18"}
    assert stories[0]["title"] == STARTERS["7-10"].title  # najświeższa — od niej startuje demo

    smok = stories[0]
    assert smok["segment_count"] == 1 and smok["last_human_author_id"] is None  # Zosia może pisać od razu
    assert any(s["segment_count"] >= 4 for s in stories)

    # „Na topie” od razu ma historie
    assert client.get("/api/stories/trending", headers=jury).json()

    # Poprawki: zaakceptowane już w tekście, lista „Do poprawienia” niepusta dla jury
    corrs = client.get("/api/corrections", headers=jury).json()
    assert counts["corrections"] == len(corrs) >= 3
    assert {c["status"] for c in corrs} == {"accepted", "rejected"}
    assert all(c["story_title"] != STARTERS["7-10"].title for c in corrs)
    for c in corrs:
        seg = next(x for x in client.get(f"/api/stories/{c['story_id']}", headers=jury).json()["segments"]
                   if x["id"] == c["segment_id"])
        assert (c["proposed"] if c["status"] == "accepted" else c["original"]) in seg["text"]
    assert client.get("/api/corrections/to-fix", headers=jury).json()

    # Drugi reset też działa (idempotentnie)
    assert client.post("/api/admin/reset", headers={"X-Reset-Pin": pin}).json()["counts"] == counts


def test_seeded_evidence_is_verbatim_from_earlier_text(client, pin, engine):
    assert client.post("/api/admin/reset", headers={"X-Reset-Pin": pin}).status_code == 200
    with Session(engine) as s:
        comp = s.exec(select(AIReview).where(AIReview.kind == ReviewKind.comprehension)).all()
        assert len(comp) >= 8
        for r in comp:
            seg = s.get(Segment, r.segment_id)
            earlier = s.exec(
                select(Segment).where(
                    Segment.story_id == seg.story_id,
                    Segment.status == SegmentStatus.approved,
                    Segment.position < seg.position,
                )
            ).all()
            assert r.evidence and r.evidence in "\n\n".join(x.text for x in earlier), r.evidence
            assert r.score is not None and r.reason
        for c in s.exec(select(Correction)).all():
            seg = s.get(Segment, c.segment_id)
            earlier = s.exec(
                select(Segment).where(
                    Segment.story_id == seg.story_id,
                    Segment.status == SegmentStatus.approved,
                    Segment.position < seg.position,
                )
            ).all()
            assert c.evidence and c.evidence in "\n\n".join(x.text for x in earlier), c.evidence
        # odrzucenia moderacji zapisane jako odrzucone fragmenty
        rejects = s.exec(select(AIReview).where(AIReview.kind == ReviewKind.moderation, AIReview.verdict == "reject"))
        for r in rejects.all():
            assert s.get(Segment, r.segment_id).status == SegmentStatus.rejected


def test_demo_flow_continues_smok_after_reset(client, pin):
    client.post("/api/admin/reset", headers={"X-Reset-Pin": pin})
    zosia = login(client, "Zosia", "7-10", "rabbit")
    smok = next(s for s in client.get("/api/stories", headers=zosia).json() if s["title"] == STARTERS["7-10"].title)
    r = client.post(
        f"/api/stories/{smok['id']}/segments",
        json={"text": "Fafik zadrżał, bo latarenka zgasła, a pukanie w głębi jaskini było coraz głośniejsze."},
        headers=zosia,
    )
    assert r.status_code == 200 and r.json()["segment"]["status"] == "approved"
