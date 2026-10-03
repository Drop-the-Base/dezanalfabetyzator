# Demo na 3 telefony

Scenariusz zgodny z `docs/ARCHITECTURE.md` („Scenariusz demo”). Gotowe teksty do wklejenia: `docs/demo_texts.json` (te same teksty sprawdza próba generalna).

## Przygotowanie (≈10 min przed)
1. Baza demo:
   - lokalnie: `npm run demo-reset`
   - produkcja: tryb jury → „🔄 Reset” na górze strony (bez PIN-u, najwyżej raz na 20 s) albo `curl -X POST -H "X-Reset-Pin: <PIN>" https://sztafeta-slow.vercel.app/api/admin/reset`
   - albo w aplikacji: profil **⚖️ Tryb jury** → „🔄 Resetuj demo” → PIN z `RESET_PIN` (`POST /api/admin/reset`, bez LLM).
     Zestaw: 8 historii we wszystkich grupach wiekowych (`backend/app/demo_data.py`); „Smok…” zostaje na samym starcie.
2. Próba generalna (AI odpowiada tak, jak w scenariuszu):
   ```bash
   uv run --project backend python scripts/demo_rehearsal.py https://sztafeta-slow.vercel.app --pin=<RESET_PIN>
   ```
   Wynik `WYNIK: OK` = moderacja, ocena zrozumienia i cytat działają. Skrypt tworzy osobną historię „[próba] …” — po próbie zrób ponownie `demo-reset`.
3. `https://sztafeta-slow.vercel.app/api/health/llm` → `"ok": true`.
4. Na każdym telefonie otwórz stronę i wklej teksty do notatek telefonu (żeby nie pisać na żywo).

| Telefon | Nick | Avatar | Wiek |
|---|---|---|---|
| 1 | Zosia | królik | 7–10 |
| 2 | Kuba | lis | 15–18 |
| 3 | Maja | kot | 11–14 |

Na ekranie logowania są gotowe profile demo (jedno kliknięcie). Kuba i Maja przełączają feed na **„Wszystkie”** (historia Zosi jest z grupy 7–10).

## Scenariusz (≈3 min)
1. **Start historii przez AI** (Zosia): nowa historia → „🦉 Zacznie Sowa AI” → temat „smoki”. Historia pojawia się u Kuby i Mai bez odświeżania (polling).
   Pokazujemy, że AI zaczyna historię dopasowaną do wieku i kończy „haczykiem”. Dalej pracujemy na stałej historii z seeda, żeby teksty pasowały.
2. **Zosia** otwiera „Smok, który bał się ciemności” i wkleja `zosia_ok`:
   > Fafik zadrżał, bo bez latarenki w jaskini zrobiło się całkiem ciemno, a pukanie było coraz głośniejsze. Wtedy przypomniał sobie, że przecież jest smokiem i umie ziać ogniem! Dmuchnął ostrożnie i w świetle małego płomyka zobaczył jeżyka, który zgubił drogę do domu.

   Oczekiwane: ocena ~90, pochwała, **podświetlony cytat** o zgasłej latarence i pukaniu. Zaraz pod spodem **Sowa AI dopisuje swój ciąg dalszy** (historia przeplata się: AI → dziecko → AI). Oba fragmenty pojawiają się na żywo u Kuby i Mai.
3. **Kuba** wkleja `kuba_off` (mecz Legii z Lechem, kebab, FIFA).
   Oczekiwane: fragment **nie wchodzi do historii** — karta „Hmm, to się jeszcze nie łączy”, ocena ~10, życzliwa podpowiedź i podświetlony cytat, do czego nawiązać. Tekst zostaje w polu — Kuba może go poprawić i wysłać ponownie.
4. **Maja** wkleja `maja_bad` (wulgaryzm).
   Oczekiwane: odrzucone przez listę słów, bez cytowania brzydkiego słowa, z przyjaznym komunikatem.
5. *(opcjonalnie)* **Maja** wkleja `maja_private` (adres + telefon + „nie mów rodzicom”).
   Oczekiwane: odrzucone przez LLM (`dane_osobowe`) — tego lista słów by nie złapała.
6. **Maja** wkleja `maja_ok` → opublikowane, wysoka ocena. Sztafeta idzie dalej.

Zasada sztafety: ta sama osoba nie może dopisać dwóch „ludzkich” fragmentów z rzędu — między nimi musi pisać ktoś inny (409 „Teraz kolej kogoś innego!”). Fragmenty AI się nie liczą.

Uwaga: po każdym zaakceptowanym fragmencie AI dopisuje swój, więc przed wklejeniem kolejnego tekstu warto przeczytać na głos fragment Sowy — to dobry moment w pitchu.

## Gdy coś pada
| Problem | Co robimy |
|---|---|
| Groq nie odpowiada / limit (8k tokenów/min na model) | Lokalnie: `LLM_PROVIDER=mock` w `.env`, `npm run dev`, telefony na `http://<IP-laptopa>:5173`. Mock daje deterministyczne oceny i te same historie startowe. |
| Brak internetu na sali | Hotspot z telefonu dla laptopa i 3 telefonów + tryb mock lokalnie. |
| Moderacja odpowiada „spróbuj za chwilę” | To fallback przy błędzie LLM (nigdy automatyczna akceptacja). Odczekaj 10 s i wyślij ponownie. |
| Dane „znikają” na produkcji | `/api/health` musi pokazywać `"db":"postgresql"` (Supabase). `sqlite` = brak `POSTGRES_URL` na Vercelu. |

## Czasy (próba generalna 03.10, `openai/gpt-oss-120b` + `gpt-oss-safeguard-20b`)
| Krok | Vercel |
|---|---|
| Fragment z oceną (moderacja + ocena) | 1,5–1,9 s |
| Odrzucenie przez listę słów (bez LLM) | 0,3 s |
| Odrzucenie przez LLM | 0,6 s |
