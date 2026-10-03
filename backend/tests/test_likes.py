import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "mock"

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.likes import demo_likes, trending_score
from app.db import get_session
from app.main import app
from app.models import Like, Story


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, nick, age="7-10", avatar="fox"):
    r = client.post("/api/auth/demo", json={"nick": nick, "avatar": avatar, "age_group": age})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def relay_story(client, headers) -> int:
    """Historia AI + fragment dziecka (+ ciąg dalszy AI) → ma ≥2 etapy."""
    sid = client.post("/api/stories/ai", json={"theme": "smoki"}, headers=headers).json()["id"]
    r = client.post(
        f"/api/stories/{sid}/segments",
        json={"text": "Smok Fafik wziął latarenkę i poszedł w ciemności sprawdzić, kto puka w głębi jaskini."},
        headers=headers,
    ).json()
    assert r["segment"]["status"] == "approved"
    return sid


def test_like_unlike_is_idempotent(client):
    ala, ola = login(client, "Ala"), login(client, "Ola")
    sid = client.post("/api/stories/ai", json={}, headers=ala).json()["id"]

    assert client.post(f"/api/stories/{sid}/like", headers=ala).json() == {"like_count": 1, "liked_by_me": True}
    assert client.post(f"/api/stories/{sid}/like", headers=ala).json() == {"like_count": 1, "liked_by_me": True}
    assert client.post(f"/api/stories/{sid}/like", headers=ola).json() == {"like_count": 2, "liked_by_me": True}

    story = client.get(f"/api/stories/{sid}", headers=ala).json()
    assert story["like_count"] == 2 and story["liked_by_me"] is True
    listed = {s["id"]: s for s in client.get("/api/stories", headers=ala).json()}
    assert listed[sid]["like_count"] == 2

    assert client.delete(f"/api/stories/{sid}/like", headers=ala).json() == {"like_count": 1, "liked_by_me": False}
    assert client.delete(f"/api/stories/{sid}/like", headers=ala).json() == {"like_count": 1, "liked_by_me": False}
    assert client.get(f"/api/stories/{sid}", headers=ola).json()["liked_by_me"] is True


def test_like_does_not_reorder_feed(client):
    ala = login(client, "Ala")
    first = client.post("/api/stories/ai", json={}, headers=ala).json()["id"]
    second = client.post("/api/stories/ai", json={}, headers=ala).json()["id"]
    before = client.get(f"/api/stories/{first}", headers=ala).json()["updated_at"]
    client.post(f"/api/stories/{first}/like", headers=ala)
    assert client.get(f"/api/stories/{first}", headers=ala).json()["updated_at"] == before
    assert [s["id"] for s in client.get("/api/stories", headers=ala).json()][:2] == [second, first]


def test_like_requires_login_and_story(client):
    ala = login(client, "Ala")
    assert client.post("/api/stories/1/like").status_code == 401
    assert client.post("/api/stories/999/like", headers=ala).status_code == 404


def test_trending_ranking(client, engine):
    a, b, c = login(client, "Ala"), login(client, "Bartek"), login(client, "Celina")
    hot = relay_story(client, a)
    warm = relay_story(client, b)
    old = relay_story(client, c)
    short = client.post("/api/stories/ai", json={}, headers=a).json()["id"]  # tylko 1 etap
    relay_story(client, a)  # bez polubień — nie trafia na listę

    for h in (a, b, c):
        client.post(f"/api/stories/{hot}/like", headers=h)
        client.post(f"/api/stories/{old}/like", headers=h)
        client.post(f"/api/stories/{short}/like", headers=h)
    client.post(f"/api/stories/{warm}/like", headers=a)

    # „old” ma tyle samo serduszek co „hot”, ale ostatni etap był 2 dni temu
    with Session(engine) as s:
        st = s.get(Story, old)
        st.updated_at = datetime.now(UTC) - timedelta(days=2)
        s.add(st)
        s.commit()

    r = client.get("/api/stories/trending", headers=a)
    assert r.status_code == 200
    ranked = r.json()
    assert [s["id"] for s in ranked] == [hot, warm, old]
    assert ranked[0]["like_count"] == 3 and ranked[0]["liked_by_me"] is True
    assert all(s["segment_count"] >= 2 for s in ranked)


def test_trending_empty(client):
    a = login(client, "Ala")
    assert client.get("/api/stories/trending", headers=a).json() == []


def test_trending_score_decays():
    t = datetime(2026, 10, 4, 12, tzinfo=UTC)
    assert trending_score(5, t, t) > trending_score(5, t - timedelta(hours=5), t)
    assert trending_score(3, t, t) > trending_score(1, t, t)
    assert trending_score(0, t, t) == 0
    assert trending_score(1, t.replace(tzinfo=None), t) == pytest.approx(1 / 2**1.5)


def test_demo_likes(client, engine):
    ids = [client.get("/api/auth/me", headers=login(client, n)).json()["id"] for n in ("Ala", "Ola", "Ela")]
    a = login(client, "Ala")
    s1 = client.post("/api/stories/ai", json={}, headers=a).json()["id"]
    s2 = client.post("/api/stories/ai", json={}, headers=a).json()["id"]
    with Session(engine) as s:
        demo_likes(s, {"Pierwsza": s1, "Druga": s2}, ids)
        demo_likes(s, {"Pierwsza": s1, "Druga": s2}, ids)  # idempotentne
        likes = s.exec(select(Like)).all()
    assert sum(1 for x in likes if x.story_id == s1) == 3
    assert sum(1 for x in likes if x.story_id == s2) == 2
