"""Warstwa LLM: jeden interfejs, wymienni dostawcy (Groq, Mock)."""

import json
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings

log = logging.getLogger("ai")
T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).parent / "prompts"


class LLMError(Exception):
    pass


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


class LLMProvider(Protocol):
    name: str

    def complete_json(self, task: str, system: str, user: str, schema: type[T], model: str | None = None) -> T:
        """Zwraca odpowiedź zwalidowaną schematem Pydantic albo rzuca LLMError."""
        ...


def _schema_hint(schema: type[BaseModel]) -> str:
    return (
        "\n\nOdpowiedz WYŁĄCZNIE poprawnym obiektem JSON zgodnym z tym schematem (bez komentarzy, bez markdown):\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str, timeout: float):
        from groq import Groq

        self.client = Groq(api_key=api_key, timeout=timeout, max_retries=1)
        self.model = model

    def complete_json(self, task: str, system: str, user: str, schema: type[T], model: str | None = None) -> T:
        model = model or self.model
        messages = [
            {"role": "system", "content": system + _schema_hint(schema)},
            {"role": "user", "content": user},
        ]
        last_err: Exception | None = None
        for attempt in range(2):
            t0 = time.perf_counter()
            try:
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.4 if task == "starter" else 0.1,
                )
                content = resp.choices[0].message.content or ""
                log.info(
                    "llm task=%s model=%s attempt=%d ms=%d tokens=%s",
                    task, model, attempt, (time.perf_counter() - t0) * 1000,
                    getattr(resp.usage, "total_tokens", "?"),
                )
                return schema.model_validate_json(content)
            except ValidationError as e:
                last_err = e
                messages.append({"role": "user", "content": f"Poprzednia odpowiedź była niepoprawna: {e}. Popraw."})
            except Exception as e:  # sieć, limity, timeout, zły klucz/model
                last_err = e
                log.warning("llm task=%s model=%s error=%s: %s", task, model, type(e).__name__, str(e)[:300])
        raise LLMError(f"{task}: {type(last_err).__name__}: {str(last_err)[:300]}")


@lru_cache
def get_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "groq" and s.groq_api_key:
        return GroqProvider(s.groq_api_key, s.groq_model, s.llm_timeout_s)
    from app.ai.mock import MockProvider

    return MockProvider()
