"""Tryb jury: reset bazy do zestawu historii demo (bez LLM), chroniony PIN-em z RESET_PIN."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.api.deps import SessionDep
from app.config import get_settings
from app.seed import reset_and_seed

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset")
def reset_demo(session: SessionDep, x_reset_pin: Annotated[str, Header()] = ""):
    pin = get_settings().reset_pin
    if not pin:
        raise HTTPException(403, "Reset demo jest wyłączony na tym serwerze.")
    if not secrets.compare_digest(x_reset_pin.strip().encode(), pin.encode()):
        raise HTTPException(403, "Zły PIN.")
    bind = session.get_bind()
    session.close()  # tabele będą usuwane — nie trzymamy otwartej transakcji
    return {"ok": True, "counts": reset_and_seed(bind)}
