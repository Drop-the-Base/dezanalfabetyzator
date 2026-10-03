# Instrukcje dla agenta

Projekt na HackYeah 2026 (zadanie otwarte „Artificial Intelligence”). Architektura: `docs/ARCHITECTURE.md`.
Hackathon: start 3.10 23:00, oddanie 4.10 23:00. Kod aplikacji powstaje wyłącznie w tym oknie.

## Sposób pracy
- Pracuje jeden agent; issues na GitHubie są ponumerowane w kolejności realizacji (sekcja „Zależy od”).
- Jedno issue = jeden branch `issue-<nr>-<slug>` = jeden PR z `Closes #<nr>`. Małe, działające kroki.
- Po każdym issue aplikacja musi się uruchamiać (`make dev` lub odpowiednik).
- Nie dodawaj funkcji spoza issue; pomysły zapisuj jako nowe issue z etykietą `idea`.

## Stack
- `backend/`: Python 3.12+, uv, FastAPI, SQLModel (SQLite), Pydantic v2, pytest, ruff. SQLModel: SQLite lokalnie, Postgres na produkcji.
- `frontend/`: React + Vite + TypeScript, Tailwind, mobile-first. Teksty UI po polsku.
- Deploy: Vercel (frontend statyczny + FastAPI jako funkcja Python `/api/*`), Postgres na Neonie. Bez WebSocketów — live updates przez polling.
- LLM: Groq za interfejsem `LLMProvider` (`backend/app/ai/provider.py`); zawsze istnieje `MockProvider`.

## Zasady AI
- Prompty trzymamy w `backend/app/ai/prompts/*.md`, nie w kodzie.
- Każda odpowiedź LLM to JSON walidowany modelem Pydantic; błąd → 1 retry → bezpieczny fallback (`needs_review`).
- Każda decyzja AI zapisywana w `AIReview` (model, verdict, reason, evidence, raw_json).
- Komunikaty dla dzieci: krótkie, życzliwe, bez zawstydzania, dopasowane do grupy wiekowej.
- Klucze tylko w `.env`; nigdy w repo.
