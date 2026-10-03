"""MockProvider: deterministyczne, heurystyczne odpowiedzi — testy i fallback bez sieci/klucza."""

import re

from pydantic import BaseModel

from app.ai.schemas import ComprehensionResult, ModerationResult, StoryContinuation, StoryStart

STOP = set(
    "i a w z na do że się nie to jest był była było jak ale co po od o u za przez dla też już tak tylko "
    "ten ta te tego tej jego jej ich on ona oni one my wy ja ty mu mi go ją je bardzo który która które "
    "gdy kiedy więc bo czy jeszcze potem teraz tam tu".split()
)

STARTERS = {
    "7-10": StoryStart(
        title="Smok, który bał się ciemności",
        text=(
            "W małej jaskini pod Górą Malin mieszkał smok Fafik. Fafik był duży i zielony, ale bardzo bał się "
            "ciemności. Każdej nocy zapalał swoją jedyną latarenkę. Pewnego wieczoru latarenka zgasła, "
            "a z głębi jaskini dobiegło ciche pukanie..."
        ),
    ),
    "11-14": StoryStart(
        title="Mapa z dna szuflady",
        text=(
            "Maja znalazła mapę w szufladzie biurka dziadka, pod starymi rachunkami. Papier był pożółkły, "
            "a w rogu ktoś narysował czerwonym tuszem kompas, którego igła wskazywała nie północ, lecz stary "
            "młyn za wsią. Jej brat, Antek, od razu chciał tam iść, ale Maja zauważyła coś dziwnego: pod "
            "młynem ktoś dopisał ołówkiem „Nie po zmroku”. Zegar w kuchni wybił właśnie siódmą, a słońce "
            "chowało się za lasem. Wtedy w sieni zaskrzypiały drzwi, chociaż dziadek wyjechał na cały dzień."
        ),
    ),
    "15-18": StoryStart(
        title="Wiadomość, która nie powinna istnieć",
        text=(
            "Ola dostała SMS-a o 3:12 w nocy. Nadawca: jej własny numer. Treść była krótka: „Nie idź jutro na "
            "most. Zaufaj mi. — Ty”. Uznała to za głupi żart Kacpra, który od tygodnia testował jakąś "
            "aplikację do podszywania się pod numery. Rano jednak w szkolnej grupie ktoś wrzucił zdjęcie "
            "zamkniętego mostu na Wiśle, a pod nim komentarz z jej konta, którego nigdy nie napisała. "
            "Kacper przysięgał, że nie ma z tym nic wspólnego. Na ekranie telefonu Oli pojawiło się "
            "powiadomienie: nowa wiadomość od „Ty”, wysłana za pięć minut."
        ),
    ),
}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) > 3 and w not in STOP}


def _stem(w: str) -> str:
    return w[:5]


def _section(user: str, name: str) -> str:
    m = re.search(rf"<{name}>\n?(.*?)\n?</{name}>", user, re.S)
    return m.group(1).strip() if m else ""


class MockProvider:
    name = "mock"

    def complete_json(self, task: str, system: str, user: str, schema: type[BaseModel], model: str | None = None):
        if getattr(schema, "__name__", "") == "_Ping" or "ok" in getattr(schema, "model_fields", {}):
            return schema(ok=True)
        if schema is ModerationResult:
            return ModerationResult(verdict="ok")
        if schema is StoryStart:
            age = _section(user, "age_group") or "7-10"
            return STARTERS.get(age, STARTERS["7-10"]).model_copy()
        if schema is StoryContinuation:
            return StoryContinuation(
                text=(
                    "Nagle w oddali coś zabłysło, jakby ktoś zapalił malutkie światełko. "
                    "Wszyscy zamarli i nasłuchiwali. Kto mógł tam być o tej porze?"
                )
            )
        if schema is ComprehensionResult:
            return self._comprehension(_section(user, "previous"), _section(user, "new"))
        raise ValueError(f"MockProvider: nieznany schemat {schema}")

    def _comprehension(self, previous: str, new: str) -> ComprehensionResult:
        prev_stems = {_stem(w) for w in _words(previous)}
        new_stems = {_stem(w) for w in _words(new)}
        overlap = prev_stems & new_stems
        score = min(100, 25 + 18 * len(overlap))
        sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", previous) if s.strip()]
        best = max(sentences or [""], key=lambda s: len({_stem(w) for w in _words(s)} & new_stems))
        if score >= 80:
            verdict, fb = "understood", "Świetnie! Widać, że uważnie przeczytałeś(-aś) wcześniejszą część."
        elif score >= 40:
            verdict, fb = "partially", "Dobry początek! Spróbuj mocniej nawiązać do tego, co działo się wcześniej."
        else:
            verdict = "not_understood"
            best = sentences[-1] if sentences else ""
            fb = "Hmm, Twój fragment nie łączy się z historią. Przeczytaj jeszcze raz, na czym się zatrzymała."
        return ComprehensionResult(
            score=score,
            verdict=verdict,
            feedback_for_kid=fb,
            evidence=best,
            strengths="Dopisałeś(-aś) własny pomysł — to się liczy!",
        )
