# Architektura — Sztafeta Słów (MVP)

## Idea w jednym zdaniu
Dzieci (7–18 lat) piszą historyjki „sztafetą”: czytają fragment napisany przez kogoś innego (albo przez AI) i dopisują ciąg dalszy. AI pilnuje bezpieczeństwa treści i sprawdza, czy kontynuacja świadczy o **przeczytaniu ze zrozumieniem**.

## Pętla użytkownika
```
AI (lub dziecko) zaczyna historię
        │
        ▼
Dziecko A czyta ──► pisze ciąg dalszy ──► AI: moderacja ──► AI: ocena zrozumienia ──► publikacja
                                             │ odrzucone           (komentarz + cytat z tekstu)
                                             ▼
                                   przyjazny komunikat, popraw i wyślij ponownie
        │
        ▼
Dziecko B widzi nowy fragment na swoim telefonie (live) i pisze dalej ... (pętla)
```
Zasada sztafety: nie można dopisać dwóch fragmentów pod rząd — trzeba przeczytać, co dopisał ktoś inny.

## Komponenty
```
backend/   FastAPI (Python 3.12, uv)
  app/api/       auth (demo: nick + avatar + wiek), stories (historie, fragmenty, pipeline), updates (polling)
  app/ai/
    provider.py    interfejs LLMProvider + GroqProvider (+ MockProvider: testy, praca offline)
    wordlist.py    moderacja warstwa 1: lokalna lista polskich wulgaryzmów (natychmiast, za darmo)
    services.py    moderacja (warstwa 2: LLM), start historii, ocena zrozumienia, weryfikacja cytatu
    prompts/*.md   prompty jako pliki
  app/models.py  SQLModel: User, Story, Segment, AIReview
frontend/  React + Vite + TypeScript + Tailwind (mobile-first)
  ekrany: Logowanie, Feed historii, Historia (czytanie + dopisywanie + wynik AI), Nowa historia
api/index.py   wejście funkcji Python na Vercelu (importuje backend)
```

### Decyzje techniczne
| Decyzja | Uzasadnienie |
|---|---|
| FastAPI + React w monorepo | Python tam, gdzie AI; React = pełna kontrola nad designem. |
| Vercel: statyczny frontend + FastAPI jako funkcja Python | Jeden projekt, jeden URL dla 3 telefonów, deploy z gita. |
| SQLite lokalnie, Postgres (Neon) na produkcji | Serverless nie ma trwałego dysku; zmiana bazy = zmiana `DATABASE_URL`. |
| Polling co ~1,5 s zamiast WebSocketów | Vercel nie obsługuje WebSocketów; na demo efekt „na żywo” jest taki sam. |
| Groq za interfejsem `LLMProvider` | Szybka inferencja; dostawcę zmienia się jednym env. |
| Moderacja dwuwarstwowa | Lista słów łapie oczywiste przypadki bez LLM; LLM łapie kontekst (przemoc, treści dla dorosłych, dane osobowe, nękanie). Błąd LLM → odrzucenie („spróbuj za chwilę”), nigdy automatyczna akceptacja. |
| Structured output (JSON) + walidacja Pydantic | Przewidywalne odpowiedzi; błędny JSON → 1 retry. |
| Logowanie demo | Bez danych osobowych (RODO dla dzieci); szybkie wejście na demo. |

## Rola AI
1. **Strażnik treści** — moderuje każdy fragment przed publikacją.
2. **Narrator** — zaczyna historie dopasowane do wieku i tematu, kończąc „haczykiem”.
3. **Recenzent zrozumienia** — ocenia, czy ciąg dalszy nawiązuje do postaci, faktów i sytuacji; daje dziecku krótki komentarz.

## Weryfikacja wyników AI
- Każda ocena zrozumienia zawiera **dosłowny cytat z wcześniejszego tekstu** (dowód). Backend sprawdza, że cytat naprawdę jest w tekście (inaczej go odrzuca), a frontend **podświetla go w historii** — dziecko widzi, na czym AI oparło ocenę.
- Ocena zrozumienia **nie blokuje** publikacji — AI doradza, nie cenzuruje. Blokuje tylko moderacja.
- Każda decyzja AI jest zapisana w `AIReview` (model, werdykt, uzasadnienie, surowy JSON).

## Ograniczenia
- LLM może się mylić w ocenie zrozumienia → ocena jest tylko podpowiedzią, z cytatem do sprawdzenia.
- Moderacja nie jest w 100% szczelna → dwie warstwy.
- Zależność od zewnętrznego API → `MockProvider` jako fallback.
- Logowanie tylko demonstracyjne.

## Scenariusz demo (3 telefony)
1. Telefon 1: Zosia (8 lat), telefon 2: Kuba (15 lat), telefon 3: Maja (12 lat).
2. Zosia prosi AI o nową historię „smoki” → pojawia się u wszystkich.
3. Zosia dopisuje ciąg dalszy → AI chwali i podświetla zdanie, do którego nawiązała; fragment pojawia się na żywo u Kuby i Mai.
4. Kuba dopisuje coś niezwiązanego → AI: „Hmm, smok bał się ciemności — gdzie to w Twoim fragmencie?” + podświetlony cytat.
5. Maja próbuje wulgaryzmu → odrzucone z przyjaznym komunikatem.
