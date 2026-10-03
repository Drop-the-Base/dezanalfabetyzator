"""Tryb jury: reset bazy do zestawu historii demo (bez LLM).

Domyślnie przycisk w trybie jury działa bez PIN-u (jury go nie zna), z limitem jednego resetu na
RESET_COOLDOWN_S. `RESET_REQUIRES_PIN=1` wymaga nagłówka X-Reset-Pin zgodnego z RESET_PIN.
"""

import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.api.deps import SessionDep
from app.config import get_settings
from app.seed import reset_and_seed

router = APIRouter(prefix="/api/admin", tags=["admin"])

RESET_COOLDOWN_S = 20
_last_open_reset = 0.0


@router.post("/reset")
def reset_demo(session: SessionDep, x_reset_pin: Annotated[str, Header()] = ""):
    global _last_open_reset
    s = get_settings()
    pin_ok = bool(s.reset_pin) and secrets.compare_digest(x_reset_pin.strip().encode(), s.reset_pin.encode())
    if s.reset_requires_pin and not s.reset_pin:
        raise HTTPException(403, "Reset demo jest wyłączony na tym serwerze.")
    if s.reset_requires_pin and not pin_ok:
        raise HTTPException(403, "Zły PIN.")
    if not pin_ok:
        wait = RESET_COOLDOWN_S - (time.monotonic() - _last_open_reset)
        if wait > 0:
            raise HTTPException(429, f"Demo było właśnie resetowane. Spróbuj za {int(wait) + 1} s.")
        _last_open_reset = time.monotonic()
    bind = session.get_bind()
    session.close()  # tabele będą usuwane — nie trzymamy otwartej transakcji
    return {"ok": True, "counts": reset_and_seed(bind)}
