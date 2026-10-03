"""Sesja przeżywa utratę konta w bazie (reset demo, inna instancja funkcji na Vercelu)."""

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import app


def make_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    return TestClient(app), engine


def test_token_restores_user_after_db_wipe():
    client, engine = make_client()
    try:
        token = client.post("/api/auth/demo", json={"nick": "Zosia", "avatar": "rabbit", "age_group": "7-10"}).json()[
            "token"
        ]
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["nick"] == "Zosia" and r.json()["age_group"] == "7-10"
    finally:
        app.dependency_overrides.clear()


def test_forged_or_old_token_is_rejected():
    client, _ = make_client()
    try:
        token = client.post("/api/auth/demo", json={"nick": "Kuba", "avatar": "fox", "age_group": "15-18"}).json()[
            "token"
        ]
        payload, _, _ = token.partition(".")
        for bad in ("losowy-stary-token", f"{payload}.deadbeef"):
            assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401
    finally:
        app.dependency_overrides.clear()
