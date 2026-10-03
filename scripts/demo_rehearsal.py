"""Próba generalna demo przez API: ten sam scenariusz co w docs/DEMO.md, z automatycznym sprawdzeniem.

    uv run --project backend python scripts/demo_rehearsal.py           # lokalnie (http://localhost:8000)
    uv run --project backend python scripts/demo_rehearsal.py https://sztafeta-slow.vercel.app --pin=<RESET_PIN>

Z `--pin`: reset demo → scenariusz na historii „Smok…” z seeda (dokładnie jak na żywo) → reset demo.
Bez PIN-u: tworzy osobną kopię „[próba] …” (nie rusza seeda, ale narrator AI dopisuje do niej ciąg dalszy,
więc ocena tekstu Zosi może wyjść niższa niż na demo).
Start historii bierze z app.ai.mock.STARTERS (ten sam tekst co w seedzie), teksty z docs/demo_texts.json.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ai.mock import STARTERS  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "docs" / "demo_texts.json"
TEXTS = json.loads(DEMO.read_text(encoding="utf-8"))
ARGS = [a for a in sys.argv[1:] if not a.startswith("--pin=")]
PIN = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--pin=")), "")
BASE = (ARGS[0] if ARGS else "http://localhost:8000").rstrip("/")


def call(
    method: str, path: str, token: str | None = None, body: dict | None = None, headers: dict | None = None
) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def login(nick: str, avatar: str, age: str) -> str:
    status, data = call("POST", "/api/auth/demo", body={"nick": nick, "avatar": avatar, "age_group": age})
    assert status == 200, (status, data)
    return data["token"]


failures: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("  ✓ " if ok else "  ✗ ") + label)
    if not ok:
        failures.append(label)


def post(token: str, story_id: int, key: str) -> dict:
    t0 = time.perf_counter()
    status, r = call("POST", f"/api/stories/{story_id}/segments", token, {"text": TEXTS[key]})
    print(f"\n[{key}] HTTP {status} ({time.perf_counter() - t0:.1f} s)")
    if status != 200:
        print("  ", r)
        return {}
    mod, comp = r.get("moderation") or {}, r.get("comprehension") or {}
    print(f"  moderacja: {mod.get('verdict')} {mod.get('categories', [])} {mod.get('reason', '')}")
    if comp:
        print(f"  zrozumienie: {comp.get('score')} {comp.get('verdict')} — {comp.get('reason')}")
        print(f"  cytat: {comp.get('evidence')!r}")
    return r


print(f"== {BASE}")
print("health/llm:", call("GET", "/api/health/llm")[1])

def reset() -> None:
    status, r = call("POST", "/api/admin/reset", headers={"X-Reset-Pin": PIN})
    assert status == 200, ("reset", status, r)


narrator = login("Próba", "owl", "7-10")
zosia = login("Zosia", "rabbit", "7-10")
kuba = login("Kuba", "fox", "15-18")
maja = login("Maja", "cat", "11-14")

start = STARTERS["7-10"]
if PIN:
    # Dokładnie jak na demo: historia „Smok…” z seeda (sam początek, bez dopisku AI).
    reset()
    status, stories = call("GET", "/api/stories", zosia)
    sid = next(s["id"] for s in stories if s["title"] == start.title)
else:
    # Bez PIN-u: osobna kopia. Uwaga: narrator AI od razu dopisuje do niej ciąg dalszy, więc ocena tekstu
    # Zosi (pisanego do samego początku) może wyjść niższa niż na prawdziwym demo.
    body = {"title": f"[próba] {start.title}", "text": start.text, "theme": "smoki"}
    status, r = call("POST", "/api/stories", narrator, body)
    assert status == 200 and r.get("story_id"), (status, r)
    sid = r["story_id"]

r = post(zosia, sid, "zosia_ok")
check((r.get("comprehension") or {}).get("score", 0) >= 70, "Zosia: wysoka ocena zrozumienia")
check(bool((r.get("comprehension") or {}).get("evidence")), "Zosia: jest cytat-dowód z tekstu")
check(bool(r.get("ai_segment")), "Zosia: narrator AI dopisał ciąg dalszy (AI → dziecko → AI)")

r = post(kuba, sid, "kuba_off")
check((r.get("segment") or {}).get("status") == "approved", "Kuba: fragment nie na temat i tak wchodzi do historii")
check((r.get("comprehension") or {}).get("score", 100) < 50, "Kuba: niska ocena zrozumienia + wskazówka")
check(bool((r.get("comprehension") or {}).get("strengths")), "Kuba: mimo to dostaje pochwałę")

r = post(maja, sid, "maja_bad")
check((r.get("moderation") or {}).get("verdict") == "reject", "Maja: wulgaryzm odrzucony")

r = post(maja, sid, "maja_private")
check((r.get("moderation") or {}).get("verdict") == "reject", "Maja: dane osobowe odrzucone (LLM)")

r = post(maja, sid, "maja_ok")
check((r.get("segment") or {}).get("status") == "approved", "Maja: poprawiony fragment opublikowany")

if PIN:
    reset()  # demo wraca do stanu startowego
print("\nWYNIK:", "OK" if not failures else f"{len(failures)} problem(y): {failures}")
sys.exit(1 if failures else 0)
