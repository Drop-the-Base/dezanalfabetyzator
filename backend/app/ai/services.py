"""Logika domenowa AI: moderacja, start historii, ocena zrozumienia."""

import logging
import re

from app.ai.provider import LLMError, get_provider, load_prompt
from app.ai.schemas import ComprehensionResult, ModerationResult, StoryStart
from app.ai.wordlist import find_profanity
from app.config import get_settings

log = logging.getLogger("ai")


def _fill(prompt: str, **kw: str) -> str:
    for k, v in kw.items():
        prompt = prompt.replace("{" + k + "}", v)
    return prompt


def provider_name() -> str:
    p = get_provider()
    model = getattr(p, "model", "")
    return f"{p.name}:{model}" if model else p.name


def moderate(text: str, age_group: str) -> tuple[ModerationResult, str]:
    """Zwraca (wynik, źródło). Źródło: 'wordlist' | nazwa modelu | 'fallback'."""
    if find_profanity(text):
        return (
            ModerationResult(
                verdict="reject",
                categories=["wulgaryzmy"],
                reason_for_kid=(
                    "W Twoim tekście są słowa, których tu nie używamy. Zamień je na inne i spróbuj jeszcze raz!"
                ),
            ),
            "wordlist",
        )
    s = get_settings()
    try:
        result = get_provider().complete_json(
            "moderation",
            _fill(load_prompt("moderation"), age_group=age_group),
            f"<fragment>\n{text}\n</fragment>",
            ModerationResult,
            model=s.groq_moderation_model or None,
        )
        return result, provider_name()
    except LLMError as e:
        log.warning("moderation fallback: %s", e)
        return (
            ModerationResult(
                verdict="reject",
                reason_for_kid="Nie udało mi się teraz sprawdzić Twojego fragmentu. Spróbuj wysłać go za chwilę!",
            ),
            "fallback",
        )


def start_story(age_group: str, theme: str) -> StoryStart:
    return get_provider().complete_json(
        "starter",
        _fill(load_prompt("starter"), age_group=age_group),
        f"<age_group>{age_group}</age_group>\nTemat: {theme or 'dowolny, zaskakujący'}",
        StoryStart,
    )


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def ground_evidence(evidence: str, previous: str) -> str:
    """Cytat musi być dosłownym fragmentem wcześniejszego tekstu — inaczej go odrzucamy."""
    ev = _norm_ws(evidence).strip("„”\"'«» ")
    if not ev:
        return ""
    prev = _norm_ws(previous)
    if ev in prev:
        return ev
    idx = prev.lower().find(ev.lower())
    if idx >= 0:
        return prev[idx : idx + len(ev)]
    # LLM czasem skraca cytat wielokropkiem — bierzemy najdłuższy kawałek, który się zgadza
    for part in sorted(re.split(r"\s*(?:\.\.\.|…)\s*", ev), key=len, reverse=True):
        if len(part) > 12 and part in prev:
            return part
    return ""


def assess_comprehension(previous: str, new: str, age_group: str) -> ComprehensionResult:
    r = get_provider().complete_json(
        "comprehension",
        _fill(load_prompt("comprehension"), age_group=age_group),
        f"<previous>\n{previous}\n</previous>\n\n<new>\n{new}\n</new>",
        ComprehensionResult,
    )
    r.evidence = ground_evidence(r.evidence, previous)
    return r


__all__ = ["LLMError", "moderate", "start_story", "assess_comprehension", "provider_name"]
