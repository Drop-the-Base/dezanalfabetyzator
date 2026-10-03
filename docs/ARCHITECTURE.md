# Architektura — Dezanalfabetyzator (MVP)

## Idea w jednym zdaniu
Dzieci (7–18 lat) wspólnie piszą historyjki „łańcuszkowe”: czytają fragment napisany przez kogoś innego (albo przez AI) i dopisują kontynuację. AI pilnuje bezpieczeństwa treści i sprawdza, czy kontynuacja świadczy o **przeczytaniu ze zrozumieniem**.

## Pętla użytkownika
```
AI (lub dziecko) zaczyna historię
        │
        ▼
Dziecko A czyta ──► pisze kontynuację ──► AI: moderacja ──► AI: test zrozumienia ──► publikacja (live)
                                             │ odrzucone            │ słabe zrozumienie
                                             ▼                      ▼
                                   przyjazny komunikat      komentarz + cytat z tekstu
                                   + "Nie zgadzam się"      + "Nie zgadzam się"
        │
        ▼
Dziecko B widzi nowy fragment na swoim telefonie (live polling) i pisze dalej ... (pętla)
```

## Komponenty

```
monorepo/
├── backend/   FastAPI (Python 3.12+, uv)
│   ├── api/         REST: auth (demo), stories, segments, appeals, admin
│   ├── api/updates  GET /api/updates?since=… (polling, kursor czasowy)
│   ├── ai/
│   │   ├── provider.py     interfejs LLMProvider + GroqProvider + MockProvider
│   │   ├── moderation.py   warstwa 1: lokalna lista słów (PL), warstwa 2: LLM (kategorie)
│   │   ├── starter.py      generowanie pierwszego akapitu (temat, grupa wiekowa)
│   │   ├── comprehension.py ocena spójności kontynuacji z wcześniejszym tekstem
│   │   └── prompts/        prompty jako pliki .md (wersjonowane)
│   ├── db/          SQLModel: SQLite lokalnie, Postgres (Neon) na Vercelu
│   └── main.py      aplikacja FastAPI (na Vercelu: funkcja Python pod /api/*)
└── frontend/  React + Vite + TypeScript + Tailwind (mobile-first, PWA)
    ├── screens/     Login, Feed, Story (czytanie + pisanie), Wynik AI, Panel nauczyciela
    └── lib/         klient API, hook usePolling (live updates), store
```

### Dlaczego tak
| Decyzja | Uzasadnienie |
|---|---|
| FastAPI + React w monorepo | Python tam, gdzie AI; React daje pełną kontrolę nad designem (20% oceny). |
| Vercel: statyczny frontend + FastAPI jako funkcja Python | Jeden projekt, jeden URL dla 3 telefonów, brak CORS, deploy z gita. |
| SQLite lokalnie, Postgres (Neon) na produkcji | Funkcje serverless nie mają trwałego dysku; zmiana bazy = zmiana `DATABASE_URL`. |
| Polling co ~1,5 s zamiast WebSocketów | Vercel nie obsługuje WebSocketów; polling z kursorem `since` daje efekt „na żywo” na demo. Ścieżka rozwoju: Pusher/Ably. |
| Groq za interfejsem `LLMProvider` | Szybka inferencja (ważne na demo); dostawcę można podmienić jednym env. `MockProvider` pozwala pracować offline i w testach. |
| Moderacja dwuwarstwowa | Lokalna lista słów łapie oczywiste przypadki natychmiast i za darmo; LLM łapie kontekst (przemoc, treści dla dorosłych, dane osobowe, nękanie). |
| Logowanie demo (nick + avatar + wiek) | Bez danych osobowych (RODO dla dzieci < 16 lat); szybkie wejście na demo. |
| Structured output (JSON) z walidacją Pydantic | Przewidywalne odpowiedzi AI; błędny JSON → retry → bezpieczny fallback (do moderatora). |

## Model danych
- **User**: id, nick, avatar, age_group (`7-10` | `11-14` | `15-18`), role (`kid` | `teacher`), created_at
- **Story**: id, title, theme, age_group, created_by (user_id | null = AI), created_at
- **Segment**: id, story_id, author_id (null = AI), position, text, status (`pending` | `approved` | `rejected` | `needs_review`), created_at
- **AIReview**: id, segment_id, kind (`moderation` | `comprehension`), verdict, score (0–100), reason (dla dziecka), evidence (cytat/zakres z poprzedniego fragmentu), model, raw_json, created_at
- **Appeal**: id, segment_id, user_id, message, status, resolution, resolved_by (`ai` | user_id)

## Rola AI (wymóg zadania)
1. **Strażnik treści**: moderuje każdy fragment przed publikacją.
2. **Narrator**: zaczyna historie dopasowane do wieku i tematu.
3. **Recenzent zrozumienia**: sprawdza, czy kontynuacja nawiązuje do postaci, faktów i wątków z poprzedniego tekstu; pisze krótki komentarz z cytatem.

## Weryfikacja i kontrola użytkownika (wymóg zadania)
- Każda decyzja AI ma **uzasadnienie + cytat z tekstu** (dowód), widoczne dla dziecka.
- **„Nie zgadzam się”**: odwołanie → ponowna ocena przez AI z argumentem dziecka → jeśli dalej sporne, trafia do nauczyciela.
- **Panel nauczyciela**: kolejka `needs_review`, możliwość nadpisania decyzji AI, log wszystkich decyzji AI (model, prompt, wynik).
- Wynik zrozumienia **nie blokuje** publikacji (tylko moderacja blokuje) — AI doradza, człowiek decyduje.

## Ograniczenia (do slajdu)
- LLM może się mylić w ocenie zrozumienia → miękka ocena + odwołanie + nadzór nauczyciela.
- Moderacja nie jest w 100% szczelna → dwie warstwy + przegląd człowieka dla wątpliwych.
- Zależność od zewnętrznego API → `MockProvider` jako fallback.
- Demo bez prawdziwej autoryzacji.

## Scenariusz demo (3 telefony)
1. Telefon 1 (Zosia, 8 lat), 2 (Kuba, 15 lat), 3 (nauczyciel).
2. AI startuje historię „Smok, który bał się ciemności”.
3. Zosia dopisuje fragment → pojawia się na żywo u Kuby.
4. Kuba dopisuje coś niezwiązanego → AI: „Hmm, smok miał bać się ciemności — gdzie to w Twoim fragmencie?” + cytat.
5. Ktoś próbuje wulgaryzmu → odrzucone z przyjaznym komunikatem; nauczyciel widzi to w panelu.
6. Kuba klika „Nie zgadzam się” → nauczyciel nadpisuje decyzję.
