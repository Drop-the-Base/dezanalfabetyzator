import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.ai.services import ground_evidence
from app.ai.wordlist import find_profanity
from app.db import get_session
from app.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

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


@pytest.mark.parametrize(
    "text",
    ["Ty kurwo jedna", "co za CHUJ", "k*u*r*w*a mać", "ja pierdolę", "k.u.r.w.a", "spierdalaj stąd", "kuuurrrwa"],
)
def test_wordlist_catches(text):
    assert find_profanity(text)


@pytest.mark.parametrize(
    "text",
    ["Smok miał piękną sukienkę i odniósł sukces.", "Hubert nacisnął pedał roweru.", "Kot wziął szmatkę."],
)
def test_wordlist_allows_clean(text):
    assert not find_profanity(text)


def test_ground_evidence_requires_quote_from_previous():
    prev = "Smok Fafik bał się ciemności.  Latarenka zgasła."
    assert ground_evidence("„Smok Fafik bał się ciemności.”", prev) == "Smok Fafik bał się ciemności."
    assert ground_evidence("smok fafik bał się", prev) == "Smok Fafik bał się"
    assert ground_evidence("Tego nie ma w tekście", prev) == ""


def test_full_relay_flow(client):
    zosia = login(client, "Zosia")
    kuba = login(client, "Kuba", "15-18", "owl")

    story = client.post("/api/stories/ai", json={"theme": "smoki"}, headers=zosia).json()
    sid = story["id"]
    assert story["segment_count"] == 1 and story["authors"][0]["is_ai"]

    # Spójna kontynuacja → opublikowana, wysoka ocena, cytat z wcześniejszego tekstu
    r = client.post(
        f"/api/stories/{sid}/segments",
        json={"text": "Smok Fafik wziął latarenkę i poszedł w ciemności sprawdzić, kto puka w głębi jaskini."},
        headers=zosia,
    ).json()
    assert r["moderation"]["verdict"] == "ok"
    assert r["segment"]["status"] == "approved"
    assert r["comprehension"]["score"] >= 80
    assert r["comprehension"]["evidence"] in client.get(f"/api/stories/{sid}", headers=zosia).json()["segments"][0]["text"]

    # Ta sama osoba dwa razy pod rząd → blokada (sztafeta!)
    r2 = client.post(f"/api/stories/{sid}/segments", json={"text": "I jeszcze jedno zdanie ode mnie."}, headers=zosia)
    assert r2.status_code == 409

    # Oderwana kontynuacja → publikowana, ale niska ocena
    r3 = client.post(
        f"/api/stories/{sid}/segments", json={"text": "Wczoraj grałem w piłkę na boisku z kolegami."}, headers=kuba
    ).json()
    assert r3["segment"]["status"] == "approved"
    assert r3["comprehension"]["verdict"] == "not_understood"

    # Wulgaryzm → odrzucone, nie pojawia się w historii
    r4 = client.post(f"/api/stories/{sid}/segments", json={"text": "Smok powiedział: kurwa, ciemno."}, headers=zosia)
    assert r4.json()["moderation"]["verdict"] == "reject"
    detail = client.get(f"/api/stories/{sid}", headers=zosia).json()
    assert len(detail["segments"]) == 3
    assert {a["nick"] for a in detail["authors"]} == {"Narrator AI", "Zosia", "Kuba"}


def test_updates_polling(client):
    a = login(client, "Ala")
    first = client.get("/api/updates", headers=a).json()
    sid = client.post("/api/stories/ai", json={}, headers=a).json()["id"]
    upd = client.get("/api/updates", params={"since": first["cursor"]}, headers=a).json()
    assert any(s["id"] == sid for s in upd["stories"])
    assert any(s["story_id"] == sid for s in upd["segments"])


def test_requires_login(client):
    assert client.get("/api/stories").status_code == 401
