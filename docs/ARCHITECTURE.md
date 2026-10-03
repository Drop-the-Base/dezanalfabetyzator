# Architektura — Sztafeta Słów (MVP)

## Idea w jednym zdaniu
Dzieci (7–18 lat) piszą historyjki „sztafetą” na zmianę z AI: AI → dziecko → AI → dziecko… Każde dziecko czyta to, co było wcześniej, i dopisuje ciąg dalszy, a narrator AI od razu odpowiada swoim fragmentem. AI pilnuje bezpieczeństwa treści i sprawdza, czy kontynuacja świadczy o **przeczytaniu ze zrozumieniem**.

## Pętla użytkownika
```
AI (lub dziecko) zaczyna historię
        │
        ▼
Dziecko A czyta ──► pisze ciąg dalszy ──► AI: moderacja ──► AI: ocena zrozumienia ──► publikacja ──► AI: narrator dopisuje swój fragment
                                             │ odrzucone           │ „nie łączy się”
                                             ▼                     ▼
                         przyjazny komunikat; tekst zostaje w polu, dziecko poprawia i wysyła ponownie
        │
        ▼
Dziecko B widzi oba nowe fragmenty na swoim telefonie (live) i pisze dalej ... (pętla)
```
Zasada sztafety: między fragmentami AI piszą różne dzieci — ta sama osoba nie dopisze dwóch „ludzkich” fragmentów z rzędu, trzeba przeczytać, co dopisał ktoś inny.

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
- Fragment ocenony jako **„nie łączy się z historią”** nie wchodzi do historii — dziecko dostaje wskazówkę z cytatem i poprawia swój tekst (zostaje w polu). Ocena „częściowo” przepuszcza fragment. Awaria LLM przy ocenie nie blokuje dzieci.
- Każda decyzja AI jest zapisana w `AIReview` (model, werdykt, uzasadnienie, surowy JSON).

## Ograniczenia
- LLM może się mylić w ocenie zrozumienia → ocena jest tylko podpowiedzią, z cytatem do sprawdzenia.
- Moderacja nie jest w 100% szczelna → dwie warstwy.
- Zależność od zewnętrznego API → `MockProvider` jako fallback. Darmowy limit Groq: 8000 tokenów/min na model → moderacja na osobnym modelu (`gpt-oss-safeguard-20b`).
- Logowanie tylko demonstracyjne.

## Scenariusz demo (3 telefony)
1. Telefon 1: Zosia (8 lat), telefon 2: Kuba (15 lat), telefon 3: Maja (12 lat).
2. Zosia prosi AI o nową historię „smoki” → pojawia się u wszystkich.
3. Zosia dopisuje ciąg dalszy → AI chwali i podświetla zdanie, do którego nawiązała; fragment pojawia się na żywo u Kuby i Mai.
4. Kuba dopisuje coś niezwiązanego → AI: „Hmm, smok bał się ciemności — gdzie to w Twoim fragmencie?” + podświetlony cytat.
5. Maja próbuje wulgaryzmu → odrzucone z przyjaznym komunikatem.
