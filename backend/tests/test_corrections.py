import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.ai import services as ai
from app.ai.provider import LLMError
from app.api.corrections import DemoCorrection, demo_corrections
from app.db import get_session
from app.main import app
from app.models import Correction, Segment, User

ZOSIA_TEXT = "Smok Fafik wziął latarenkę i poszedł w ciemności sprawdzić, kto puka w głębi jaskini."


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


@pytest.fixture
def story(client):
    """Historia AI + fragment Zosi (+ ciąg dalszy narratora). Zwraca (story_id, id fragmentu Zosi, nagłówki)."""
    zosia = login(client, "Zosia")
    kuba = login(client, "Kuba", avatar="owl")
    sid = client.post("/api/stories/ai", json={"theme": "smoki"}, headers=zosia).json()["id"]
    r = client.post(f"/api/stories/{sid}/segments", json={"text": ZOSIA_TEXT}, headers=zosia).json()
    assert r["segment"]["status"] == "approved"
    return sid, r["segment"]["id"], zosia, kuba


def correct(client, seg_id, headers, original, proposed, reason=""):
    return client.post(
        f"/api/segments/{seg_id}/corrections",
        json={"original": original, "proposed": proposed, "reason": reason},
        headers=headers,
    )


def test_accepted_correction_updates_segment(client, story):
    sid, seg_id, zosia, kuba = story
    cursor = client.get("/api/updates", headers=kuba).json()["cursor"]

    r = correct(client, seg_id, kuba, "wziął latarenkę", "wziął zgaszoną latarenkę z jaskini", "latarenka zgasła")
    assert r.status_code == 200
    body = r.json()
    c = body["correction"]
    assert c["status"] == "accepted"
    assert c["author"]["nick"] == "Kuba" and c["segment_author"]["nick"] == "Zosia"
    assert c["ai_feedback"] and c["model"] == "mock"
    first_text = client.get(f"/api/stories/{sid}", headers=kuba).json()["segments"][0]["text"]
    assert c["evidence"] and c["evidence"] in first_text  # cytat z WCZEŚNIEJSZEGO tekstu
    assert "zgaszoną latarenkę z jaskini" in body["segment"]["text"]

    # Tekst podmieniony w historii i widoczny w live pollingu
    seg = next(s for s in client.get(f"/api/stories/{sid}", headers=zosia).json()["segments"] if s["id"] == seg_id)
    assert seg["text"].startswith("Smok Fafik wziął zgaszoną latarenkę z jaskini i poszedł")
    upd = client.get("/api/updates", params={"since": cursor}, headers=zosia).json()
    assert any(s["id"] == seg_id and "zgaszoną" in s["text"] for s in upd["segments"])
    assert any(s["id"] == sid for s in upd["stories"])

    # Listy poprawek
    recent = client.get("/api/corrections", headers=zosia).json()
    assert recent[0]["id"] == c["id"] and recent[0]["story_title"]
    assert recent[0]["original"] == "wziął latarenkę"
    assert [x["id"] for x in client.get(f"/api/segments/{seg_id}/corrections", headers=zosia).json()] == [c["id"]]
    assert [x["status"] for x in client.get(f"/api/stories/{sid}/corrections", headers=zosia).json()] == ["accepted"]


def test_rejected_correction_keeps_text(client, story, engine):
    sid, seg_id, zosia, kuba = story
    r = correct(client, seg_id, kuba, "latarenkę", "rower").json()
    assert r["correction"]["status"] == "rejected"
    assert r["correction"]["ai_feedback"]
    assert r["segment"]["text"] == ZOSIA_TEXT
    with Session(engine) as s:
        stored = s.exec(select(Correction)).one()
        assert stored.raw_json and '"rejected"' in stored.raw_json


def test_correction_validation(client, story):
    sid, seg_id, zosia, kuba = story
    assert correct(client, seg_id, zosia, "latarenkę", "lampę").status_code == 403  # własny fragment
    assert correct(client, seg_id, kuba, "tego nie ma w tekście", "coś").status_code == 422
    assert correct(client, seg_id, kuba, "latarenkę", "latarenkę").status_code == 422
    assert correct(client, 9999, kuba, "a", "b").status_code == 404
    # Fragmenty narratora AI też można poprawiać
    ai_seg = client.get(f"/api/stories/{sid}", headers=kuba).json()["segments"][0]
    assert ai_seg["author"]["is_ai"]
    assert correct(client, ai_seg["id"], kuba, "Fafik", "Fafik").status_code == 422
    assert correct(client, ai_seg["id"], kuba, "Fafik był duży", "Fafik był wielki").status_code == 200


def test_profanity_is_blocked(client, story):
    _, seg_id, _, kuba = story
    r = correct(client, seg_id, kuba, "latarenkę", "kurwa latarenkę").json()
    assert r["blocked_by_moderation"] is True
    assert r["correction"]["status"] == "rejected"
    assert r["correction"]["model"] == "wordlist"
    assert r["segment"]["text"] == ZOSIA_TEXT


def test_llm_failure_never_auto_accepts(client, story, monkeypatch):
    _, seg_id, _, kuba = story

    def boom(*a, **kw):
        raise LLMError("correction: timeout")

    monkeypatch.setattr(ai, "judge_correction", boom)
    r = correct(client, seg_id, kuba, "wziął latarenkę", "wziął zgaszoną latarenkę z jaskini").json()
    assert r["correction"]["status"] == "rejected"
    assert r["correction"]["model"] == "fallback"
    assert "za chwilę" in r["correction"]["ai_feedback"]
    assert r["segment"]["text"] == ZOSIA_TEXT


def test_to_fix_lists_partial_segments(client, story, engine):
    _, seg_id, zosia, kuba = story
    with Session(engine) as s:
        seg = s.get(Segment, seg_id)
        seg.comprehension_score = 55
        s.add(seg)
        s.commit()
    assert [x["segment"]["id"] for x in client.get("/api/corrections/to-fix", headers=kuba).json()] == [seg_id]
    assert client.get("/api/corrections/to-fix", headers=zosia).json() == []  # własnych nie pokazujemy
    correct(client, seg_id, kuba, "wziął latarenkę", "wziął zgaszoną latarenkę z jaskini")
    assert client.get("/api/corrections/to-fix", headers=kuba).json() == []  # już poprawione


def test_demo_corrections_helper(client, story, engine):
    sid, seg_id, _, _ = story
    with Session(engine) as s:
        seg = s.get(Segment, seg_id)
        kuba = s.exec(select(User).where(User.nick == "Kuba")).one()
        zosia = s.exec(select(User).where(User.nick == "Zosia")).one()
        made = demo_corrections(
            s,
            [
                DemoCorrection(seg, kuba, "latarenkę", "zgaszoną latarenkę", True, "Brawo!", "latarenka zgasła"),
                DemoCorrection(seg, kuba, "w głębi", "na dachu", False, "Pukanie było w jaskini."),
                DemoCorrection(seg, kuba, "nie ma tego", "x", True, "-"),  # pominięte: brak w tekście
                DemoCorrection(seg, zosia, "Smok", "Smoczek", True, "-"),  # pominięte: własny fragment
            ],
        )
        assert [c.status for c in made] == ["accepted", "rejected"]
        assert "zgaszoną latarenkę" in s.get(Segment, seg_id).text
        assert all(c.model == "demo" and c.raw_json for c in made)
    shown = client.get(f"/api/stories/{sid}/corrections", headers=login(client, "Ola")).json()
    assert sorted(c["status"] for c in shown) == ["accepted", "rejected"]


def test_weak_but_related_segment_stays_and_is_to_fix(client, story, monkeypatch):
    """Mniej spójny fragment zostaje w historii (blokuje tylko moderacja) i trafia do „Do poprawienia”."""
    sid, _, zosia, kuba = story
    real = ai.assess_comprehension

    def weak(previous, new, age_group):
        r = real(previous, new, age_group)
        r.score, r.verdict = 5, "not_understood"
        return r

    monkeypatch.setattr(ai, "assess_comprehension", weak)
    text = "Fafik coś usłyszał w jaskini i poszedł spać."
    r = client.post(f"/api/stories/{sid}/segments", json={"text": text}, headers=kuba).json()
    assert r["segment"]["status"] == "approved"
    to_fix = client.get("/api/corrections/to-fix", headers=zosia).json()
    assert r["segment"]["id"] in [t["segment"]["id"] for t in to_fix]
