# Sztafeta Słów (Dezanalfabetyzator)

HackYeah 2026 — zadanie otwarte **Artificial Intelligence** · zespół **Drop the Base**

Wspólne pisanie historyjek przez dzieci i młodzież (7–18 lat). Dziecko czyta fragment napisany przez kogoś innego (lub przez AI) i dopisuje kontynuację. AI:

1. **moderuje** treści (wulgaryzmy, nieodpowiednie tematy) przed publikacją,
2. **zaczyna** historie dopasowane do wieku,
3. **sprawdza zrozumienie**: czy kontynuacja nawiązuje do tego, co było wcześniej, i komentuje z cytatem z tekstu.

Każda ocena AI pokazuje cytat z tekstu, na którym się opiera — podświetlony w historii.

- Architektura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Plan prac: [Issues](https://github.com/Drop-the-Base/dezanalfabetyzator/issues)

> Status: planowanie. Kod aplikacji powstaje w trakcie hackathonu (od 3.10.2026, 23:00).

## Uruchomienie lokalnie
Wymagane: [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
cp .env.example .env          # wpisz GROQ_API_KEY i LLM_PROVIDER=groq (bez klucza działa tryb mock)
npm install && npm run setup  # zależności backendu (uv) i frontendu
npm run demo-reset            # baza z historiami demo
npm run dev                   # backend :8000 + frontend :5173
```
Telefony w tej samej sieci Wi-Fi: `http://<IP-komputera>:5173`.

Inne: `npm test` (testy backendu), `npm run lint`. Po zmianie zależności backendu zaktualizuj też `requirements.txt` (Vercel).

## Deploy (Vercel)
- Frontend: statyczny build `frontend/dist` (`scripts/vercel-build.sh`); backend: `api/index.py` (FastAPI jako funkcja Python). Konfiguracja w `vercel.json`.
- Zmienne środowiskowe: `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL`, `DATABASE_URL` (Neon Postgres z Vercel Marketplace).
- Bez `DATABASE_URL` aplikacja używa SQLite w `/tmp` — działa, ale dane znikają (tylko do pierwszego testu).
- Dane demo na produkcji: `DATABASE_URL=<neon-url> npm run seed`.
