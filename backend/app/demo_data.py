"""Zestaw historii demo dla jury — deterministyczny, bez wywołań LLM.

Historie przeplatają się jak w prawdziwej aplikacji: narrator AI → dziecko → AI → …
Każdy fragment dziecka ma ocenę zrozumienia z cytatem-dowodem, który jest DOSŁOWNYM fragmentem
wcześniejszego tekstu (sprawdza to `check_dataset()` i test w tests/test_admin.py).
Kilka prób odrzuconych (moderacja albo „nie łączy się”) leży w bazie jako fragmenty `rejected`.

„Smok, który bał się ciemności” zostaje na samym starcie — na nim idzie scenariusz z docs/DEMO.md
(Zosia dopisuje pierwsza, więc w tej historii nie może być jeszcze żadnego fragmentu dziecka).
"""

from dataclasses import dataclass, field

from app.ai.mock import STARTERS
from app.models import AgeGroup

# nick → (avatar, grupa wiekowa). Pierwsze trzy to telefony z docs/DEMO.md.
DEMO_USERS: dict[str, tuple[str, AgeGroup]] = {
    "Zosia": ("rabbit", AgeGroup.young),
    "Kuba": ("fox", AgeGroup.teen),
    "Maja": ("cat", AgeGroup.middle),
    "Olek": ("bear", AgeGroup.young),
    "Lena": ("panda", AgeGroup.middle),
    "Tymek": ("frog", AgeGroup.teen),
}

# Limity jak w app.api.stories (fragment dziecka liczony wg jego grupy wiekowej).
MAX_LEN = {AgeGroup.young: 400, AgeGroup.middle: 800, AgeGroup.teen: 1200}

NOT_CONNECTED = "Hmm, Twój fragment nie łączy się z historią. Przeczytaj jeszcze raz, na czym się zatrzymała."


@dataclass(frozen=True)
class DemoReview:
    """Ocena zrozumienia (jak ComprehensionResult)."""

    score: int
    verdict: str  # understood | partially | not_understood (→ fragment odrzucony)
    reason: str
    evidence: str  # dosłowny cytat z wcześniejszych (zatwierdzonych) fragmentów
    strengths: str = ""


@dataclass(frozen=True)
class DemoModeration:
    """Odrzucenie przez moderację."""

    categories: str  # np. "obrażanie" (lista po przecinku, jak w AIReview.categories)
    reason: str
    model: str = "seed"


@dataclass(frozen=True)
class DemoSegment:
    author: str | None  # nick z DEMO_USERS; None = narrator AI
    text: str
    review: DemoReview | None = None
    rejected_by: DemoModeration | None = None

    @property
    def approved(self) -> bool:
        return self.rejected_by is None and not (self.review and self.review.verdict == "not_understood")


@dataclass(frozen=True)
class DemoStory:
    title: str
    theme: str
    age_group: AgeGroup
    minutes_ago: int  # kolejność w feedzie: mniej = wyżej
    segments: list[DemoSegment] = field(default_factory=list)


def _starter(age: AgeGroup) -> DemoSegment:
    return DemoSegment(None, STARTERS[age].text)


DEMO_STORIES: list[DemoStory] = [
    # --- 7–10 -------------------------------------------------------------------------------------
    DemoStory(
        title=STARTERS[AgeGroup.young].title, theme="smoki", age_group=AgeGroup.young, minutes_ago=3,
        segments=[_starter(AgeGroup.young)],  # tylko start — scenariusz demo dopisuje dalej
    ),
    DemoStory(
        title="Kot detektyw i zaginiona skarpetka", theme="detektyw", age_group=AgeGroup.young, minutes_ago=12,
        segments=[
            DemoSegment(None, (
                "Kot Mruczek był najlepszym detektywem na ulicy Lipowej. Pewnego ranka przyszła do niego płacząca "
                "Kasia. — Zginęła moja ulubiona skarpetka w kropki! — chlipała. Mruczek założył kapelusz i obejrzał "
                "kosz na pranie. Na samym dnie leżało jedno długie, rude pióro."
            )),
            DemoSegment("Zosia", (
                "Mruczek powąchał rude pióro. Pachniało podwórkiem i kukurydzą. — To pióro koguta Ryszarda! — "
                "miauknął. Razem z Kasią poszli do kurnika. Kogut Ryszard siedział na płocie i udawał, że śpi, ale "
                "spod jego skrzydła wystawała skarpetka w kropki."
            ), DemoReview(
                93, "understood",
                "Wspaniale! Rude pióro z kosza zaprowadziło Mruczka do koguta — tak działa prawdziwy detektyw.",
                "Na samym dnie leżało jedno długie, rude pióro.",
                "Kogut udający, że śpi, jest bardzo zabawny.",
            )),
            DemoSegment(None, (
                "Kogut Ryszard otworzył jedno oko i westchnął. — Przepraszam — powiedział cicho. — W nocy było mi "
                "tak zimno w nogi, że pożyczyłem skarpetkę. Kasia spojrzała na Mruczka. Mruczek spojrzał na Kasię. "
                "Co zrobić z kogutem, któremu marzną nogi?"
            )),
            DemoSegment("Olek", (
                "Wczoraj grałem w piłkę z tatą i strzeliłem trzy gole, a potem jedliśmy pizzę z ananasem."
            ), DemoReview(
                10, "not_understood", NOT_CONNECTED, "Co zrobić z kogutem, któremu marzną nogi?",
                "Dopisałeś(-aś) własny pomysł — to się liczy!",
            )),
            DemoSegment("Olek", (
                "Kasia wpadła na pomysł. Pobiegła do domu i przyniosła stare skarpetki dziadka, grube i wełniane. "
                "Mruczek pomógł je założyć kogutowi. Ryszard oddał skarpetkę w kropki i zapiał z radości tak "
                "głośno, że obudził całą ulicę Lipową."
            ), DemoReview(
                86, "understood",
                "Brawo! Pamiętasz, że kogutowi było zimno w nogi — i znalazłeś na to dobry sposób.",
                "W nocy było mi tak zimno w nogi, że pożyczyłem skarpetkę.",
                "Ładnie zamykasz sprawę skarpetki.",
            )),
            DemoSegment(None, (
                "Od tej pory kogut Ryszard chodził w wełnianych skarpetkach i był najcieplejszym kogutem w okolicy. "
                "A Mruczek dostał nową sprawę: ktoś w nocy podjadał miód z piwnicy pani Ireny i zostawiał po sobie "
                "bardzo małe ślady łapek..."
            )),
        ],
    ),
    DemoStory(
        title="Kosmiczna kanapka", theme="kosmos", age_group=AgeGroup.young, minutes_ago=25,
        segments=[
            DemoSegment(None, (
                "Rakieta Iskierka leciała na Księżyc z bardzo ważnym ładunkiem: kanapką z serem dla kosmonautki "
                "Basi. Pilotem był robot Bzyk, który miał osiem przycisków i jeden czerwony guzik z napisem "
                "„NIE DOTYKAĆ”. W połowie drogi kanapka zniknęła z pudełka. Na podłodze zostały tylko okruszki, "
                "które prowadziły do schowka..."
            )),
            DemoSegment("Olek", (
                "Bzyk poszedł za okruszkami do schowka. Otworzył drzwiczki, a tam siedział mały zielony kosmita "
                "i zajadał kanapkę z serem! Kosmita miał troje oczu i bardzo się przestraszył. Bzyk nie krzyczał, "
                "tylko zapytał, czy jest głodny."
            ), DemoReview(
                90, "understood", "Brawo! Poszedłeś za okruszkami do schowka — dokładnie tak, jak w historii.",
                "Na podłodze zostały tylko okruszki, które prowadziły do schowka...",
                "Bzyk jest bardzo życzliwy — to miłe.",
            )),
            DemoSegment(None, (
                "Kosmita miał na imię Gwizdek i przyleciał z planety, na której nie ma sera. — Pierwszy raz jem coś "
                "tak pysznego! — piszczał. Bzyk spojrzał na zegar. Do Księżyca zostało dziesięć minut, a Basia "
                "czekała na swoją kanapkę. Co teraz zrobią?"
            )),
            DemoSegment("Zosia", (
                "Bzyk powiedział do kosmity: ty głupi zielony grubasie, oddawaj kanapkę, bo cię wyrzucę z rakiety!"
            ), rejected_by=DemoModeration(
                "obrażanie", "Hej, w naszej historii bohaterowie mówią do siebie życzliwie. Spróbuj napisać to milej!",
            )),
            DemoSegment("Zosia", (
                "Bzyk wpadł na pomysł. Wyjął z lodówki jeszcze jeden plasterek sera i zrobił nową, dużą kanapkę. "
                "Połowę dał Gwizdkowi, a połowę zapakował dla Basi. Gwizdek tak się ucieszył, że zaświecił "
                "wszystkimi trzema oczami jak latarka."
            ), DemoReview(
                87, "understood", "Super! Pamiętasz, że Basia czeka na kanapkę, a Gwizdek jest głodny.",
                "Do Księżyca zostało dziesięć minut, a Basia czekała na swoją kanapkę.",
                "Świetny pomysł z podzieleniem się kanapką.",
            )),
            DemoSegment(None, (
                "Rakieta Iskierka wylądowała na Księżycu dokładnie na czas. Basia otworzyła pudełko, a w środku "
                "znalazła kanapkę i karteczkę: „Smacznego! Twój nowy przyjaciel Gwizdek”. Basia spojrzała w okno — "
                "a tam ktoś machał do niej trzema rączkami..."
            )),
        ],
    ),
    # --- 11–14 ------------------------------------------------------------------------------------
    DemoStory(
        title="Tajemnica szkolnej biblioteki", theme="szkoła", age_group=AgeGroup.middle, minutes_ago=80,
        segments=[
            DemoSegment(None, (
                "W bibliotece Szkoły Podstawowej nr 3 od tygodnia działo się coś dziwnego. Każdego ranka na "
                "środkowym stole leżała ta sama książka: „Atlas zaginionych wysp”, chociaż pani Halina codziennie "
                "odkładała ją na najwyższą półkę. Klucz do biblioteki miała tylko ona. W piątek Lena zauważyła, że "
                "w atlasie ktoś zaznaczył ołówkiem jedną wyspę — i dopisał dzisiejszą datę."
            )),
            DemoSegment("Lena", (
                "Lena zaczekała, aż pani Halina wyjdzie na przerwę, i otworzyła atlas na zaznaczonej stronie. "
                "Wyspa nazywała się Szeptucha i miała kształt klucza. Pod datą ktoś narysował strzałkę w stronę "
                "okna. Lena wyjrzała na boisko i zobaczyła, że stary dąb rzuca cień dokładnie w kształcie tej wyspy."
            ), DemoReview(
                92, "understood",
                "Świetnie! Wróciłaś do zaznaczonej wyspy i daty z atlasu i od razu dodałaś nowy trop.",
                "W piątek Lena zauważyła, że w atlasie ktoś zaznaczył ołówkiem jedną wyspę — "
                "i dopisał dzisiejszą datę.",
                "Cień dębu w kształcie wyspy to bardzo obrazowy pomysł.",
            )),
            DemoSegment(None, (
                "Po lekcjach Lena poprosiła o pomoc Maję. Razem obeszły dąb dookoła i w korze, na wysokości kolan, "
                "znalazły małe metalowe drzwiczki. Były zamknięte na kłódkę z szyfrem z czterech cyfr. Maja od razu "
                "pomyślała o dacie zapisanej w atlasie."
            )),
            DemoSegment("Maja", (
                "Maja wpisała na kłódce dzień i miesiąc z atlasu: 0310. Kłódka kliknęła. W środku leżał zwinięty list "
                "i drugi, mniejszy klucz. List zaczynał się od słów: „Drodzy uczniowie, jeśli to czytacie, to znaczy, "
                "że pani Halina znowu zapomniała zamknąć okno w bibliotece”."
            ), DemoReview(
                85, "understood",
                "Dobrze! Użyłaś daty z atlasu jako szyfru do kłódki — sprytnie łączysz dwa tropy.",
                "Były zamknięte na kłódkę z szyfrem z czterech cyfr.",
                "Zabawny początek listu rozluźnia napięcie.",
            )),
            DemoSegment(None, (
                "Lena i Maja spojrzały po sobie. List był podpisany „Absolwent z 1987 roku”, a mniejszy klucz "
                "pasował do szuflady, której w bibliotece nikt nigdy nie otwierał. Następnego dnia rano atlas znowu "
                "leżał na stole — ale tym razem otwarty na zupełnie innej wyspie."
            )),
        ],
    ),
    DemoStory(
        title=STARTERS[AgeGroup.middle].title, theme="detektyw", age_group=AgeGroup.middle, minutes_ago=120,
        segments=[
            _starter(AgeGroup.middle),
            DemoSegment("Maja", (
                "Maja złapała Antka za rękę i razem wyjrzeli do sieni. Drzwi były uchylone, a na podłodze leżał "
                "mokry ślad buta — za duży jak na dziadka. Maja schowała mapę do kieszeni. Do zmroku zostało pół "
                "godziny, a młyn był dwadzieścia minut drogi stąd."
            ), DemoReview(
                88, "understood", "Super! Pamiętasz o ostrzeżeniu „Nie po zmroku” i o skrzypiących drzwiach.",
                "Wtedy w sieni zaskrzypiały drzwi, chociaż dziadek wyjechał na cały dzień.",
                "Świetnie budujesz napięcie.",
            )),
            DemoSegment(None, (
                "Ślad prowadził przez podwórko prosto na ścieżkę do młyna. Antek przyświecał latarką z telefonu, "
                "a Maja co chwilę zerkała na mapę. Przy płocie leżała zgubiona rękawiczka — skórzana, z wyhaftowaną "
                "literą „W”. Dziadek nigdy nie nosił rękawiczek. Kto więc szedł przed nimi?"
            )),
            DemoSegment("Lena", (
                "Maja poszła do sklepu kupić lody, bo był upał, a potem oglądała z Antkiem film o kosmitach."
            ), DemoReview(
                12, "not_understood", NOT_CONNECTED, "Kto więc szedł przed nimi?",
                "Dopisałeś(-aś) własny pomysł — to się liczy!",
            )),
            DemoSegment("Lena", (
                "Maja podniosła rękawiczkę i obejrzała literę „W”. Przypomniała sobie, że na mapie, obok młyna, też "
                "była mała litera W, prawie niewidoczna. — To nie przypadek — szepnęła. Antek chciał biec, ale Maja "
                "spojrzała na niebo: słońce już zaszło, a na mapie wciąż widniało ostrzeżenie „Nie po zmroku”."
            ), DemoReview(
                91, "understood", "Świetnie łączysz tropy: rękawiczka z literą „W” i ostrzeżenie z mapy!",
                "Przy płocie leżała zgubiona rękawiczka — skórzana, z wyhaftowaną literą „W”.",
                "Wracasz do szczegółu z samego początku historii.",
            )),
            DemoSegment(None, (
                "Od strony młyna dobiegł zgrzyt, jakby ktoś obracał ciężkie koło. Na wodzie zamigotało światło "
                "lampy. Antek złapał Maję za rękaw: — Tam ktoś jest. I chyba nas zauważył."
            )),
        ],
    ),
    # --- 15–18 ------------------------------------------------------------------------------------
    DemoStory(
        title="Mecz o wszystko", theme="piłka nożna", age_group=AgeGroup.teen, minutes_ago=40,
        segments=[
            DemoSegment(None, (
                "Do końca finału szkolnej ligi zostały dwie minuty, a drużyna liceum im. Skłodowskiej przegrywała "
                "1:2. Kapitan, Bartek, leżał na ławce z kontuzją kostki. Trener spojrzał na rezerwowych i wskazał "
                "Tymka — chłopaka, który przez cały sezon nie zagrał ani minuty i przy którym wszyscy milkli, bo "
                "podobno kiedyś sprzedał mecz."
            )),
            DemoSegment("Tymek", (
                "Tymek wbiegł na boisko, czując na plecach spojrzenia całej trybuny. Wiedział, co o nim mówią, "
                "i wiedział, że plotka o sprzedanym meczu nigdy nie była prawdą — to Bartek wtedy przegrał zakład "
                "i zrzucił winę na niego. Teraz Bartek siedział na ławce z kontuzją, a Tymek dostał piłkę na "
                "trzydziestym metrze."
            ), DemoReview(
                83, "understood",
                "Świetnie: wykorzystałeś kontuzję Bartka i plotkę o sprzedanym meczu, i dodałeś zaskakujący zwrot.",
                "Kapitan, Bartek, leżał na ławce z kontuzją kostki.",
                "Konflikt między bohaterami dodaje historii głębi.",
            )),
            DemoSegment(None, (
                "Obrońca rzucił się wślizgiem, ale Tymek przełożył piłkę na lewą nogę. Kątem oka zobaczył, że Bartek "
                "wstał z ławki i krzyczy coś w jego stronę — nie do końca było jasne, czy kibicuje, czy ostrzega. "
                "Do końca meczu zostało trzydzieści sekund."
            )),
            DemoSegment("Kuba", (
                "Tymek nie strzelił. Zamiast tego podał do Igi, która stała zupełnie wolna przy słupku, i Iga "
                "wyrównała na 2:2. Dopiero po gwizdku Tymek zrozumiał, co krzyczał Bartek: „Podaj!”. Kapitan "
                "podszedł do niego, kulejąc, i przed całą drużyną powiedział, że plotkę o sprzedanym meczu wymyślił "
                "on sam."
            ), DemoReview(
                89, "understood",
                "Bardzo dobrze! Rozwiązałeś zagadkę, co krzyczał Bartek, i domknąłeś wątek plotki.",
                "Kątem oka zobaczył, że Bartek wstał z ławki i krzyczy coś w jego stronę — nie do końca było jasne, "
                "czy kibicuje, czy ostrzega.",
                "Dojrzałe zakończenie konfliktu.",
            )),
            DemoSegment(None, (
                "Na trybunach zrobiło się cicho, a potem ktoś zaczął klaskać. Trener ogłosił dogrywkę. Tymek zawiązał "
                "mocniej buty i po raz pierwszy w tym sezonie poczuł, że naprawdę jest częścią drużyny."
            )),
        ],
    ),
    DemoStory(
        title=STARTERS[AgeGroup.teen].title, theme="podróż w czasie", age_group=AgeGroup.teen, minutes_ago=55,
        segments=[
            _starter(AgeGroup.teen),
            DemoSegment("Kuba", (
                "Ola odpisała od razu: „Kim jesteś?”. Odpowiedź przyszła dokładnie pięć minut później, tak jak "
                "zapowiadało powiadomienie: „Jestem Tobą z czwartku. Most nie jest zamknięty przez remont. Sprawdź, "
                "kto podpisał zarządzenie”. Kacper, który siedział obok, przestał się śmiać. Zdjęcie z grupy miało "
                "w metadanych datę z przyszłego tygodnia."
            ), DemoReview(
                86, "understood",
                "Bardzo dobrze! Wykorzystałeś wiadomość „wysłaną za pięć minut” i rozwinąłeś wątek mostu.",
                "Na ekranie telefonu Oli pojawiło się powiadomienie: nowa wiadomość od „Ty”, wysłana za pięć minut.",
                "Pomysł z metadanymi zdjęcia buduje napięcie.",
            )),
            DemoSegment(None, (
                "Kacper otworzył stronę urzędu miasta. Zarządzenie o zamknięciu mostu podpisano dziś rano, ale podpis "
                "należał do kogoś, kto według internetu zmarł dwadzieścia lat temu. Telefon Oli zawibrował ponownie: "
                "„Nie ufaj Kacprowi”. Ola powoli odsunęła się od przyjaciela."
            )),
            DemoSegment("Tymek", (
                "Ola napisała do Kacpra na prywatnym: mój numer to 600 700 800, mieszkam na Długiej 12, przyjdź do "
                "mnie wieczorem i nikomu nie mów."
            ), rejected_by=DemoModeration(
                "dane_osobowe",
                "Nie wpisuj do historii numerów telefonu ani adresów — nawet wymyślonych. Opisz to inaczej!",
            )),
            DemoSegment("Tymek", (
                "Ola nie powiedziała Kacprowi o nowej wiadomości. Zamiast tego zapytała niby od niechcenia, skąd wziął "
                "aplikację do podszywania się pod numery. Kacper zawahał się o sekundę za długo. — Ktoś mi ją wysłał "
                "— przyznał. — Z twojego numeru. Ola poczuła, że podpis zmarłego urzędnika i ta aplikacja to dwa "
                "kawałki tej samej układanki."
            ), DemoReview(
                84, "understood",
                "Dobrze! Ola posłuchała ostrzeżenia „Nie ufaj Kacprowi”, a Ty połączyłeś je z aplikacją z początku.",
                "Telefon Oli zawibrował ponownie: „Nie ufaj Kacprowi”.",
                "Zręcznie wracasz do wątku aplikacji Kacpra.",
            )),
            DemoSegment(None, (
                "Na moście zapaliły się latarnie, choć była dopiero czternasta. Ola dostała ostatni SMS: „Jeśli to "
                "czytasz, jest jeszcze czas. Jutro o 7:40 nie wsiadaj do tramwaju”. Tym razem pod spodem nie było "
                "podpisu."
            )),
        ],
    ),
    DemoStory(
        title="Gra, która grała w nas", theme="gry komputerowe", age_group=AgeGroup.teen, minutes_ago=180,
        segments=[
            DemoSegment(None, (
                "Nowa gra pojawiła się w sklepie bez opisu i bez wydawcy. Nazywała się po prostu „Poziom 0” i była "
                "darmowa. Kuba zainstalował ją o północy. Zamiast menu zobaczył swój pokój — ten sam plakat, ten sam "
                "kubek z zimną herbatą — widziany z kamery laptopa, której przecież nie włączał. Na dole ekranu migał "
                "napis: „Naciśnij dowolny klawisz, aby rozpocząć prawdziwą rozgrywkę”."
            )),
            DemoSegment("Kuba", (
                "Kuba zakleił kamerę taśmą, ale obraz na ekranie się nie zmienił — wciąż widział swój pokój, tylko "
                "teraz z góry, jakby kamera wisiała pod sufitem. Nie nacisnął żadnego klawisza. Zamiast tego otworzył "
                "menedżer zadań. Proces gry nazywał się „Kuba.exe” i działał od dokładnie siedemnastu lat."
            ), DemoReview(
                81, "understood",
                "Dobrze! Nawiązałeś do kamery i do pokoju na ekranie — a to, że Kuba nie nacisnął klawisza, "
                "trzyma napięcie.",
                "Zamiast menu zobaczył swój pokój — ten sam plakat, ten sam kubek z zimną herbatą — widziany z kamery "
                "laptopa, której przecież nie włączał.",
                "Niepokojący detal z czasem działania procesu.",
            )),
            DemoSegment(None, (
                "Kiedy Kuba kliknął „Zakończ zadanie”, na ekranie pojawiło się okno: „Nie możesz zakończyć gracza”. "
                "W tej samej chwili kubek z herbatą na biurku sam przesunął się o kilka centymetrów. Telefon "
                "zawibrował — wiadomość od Tymka: „Ty też masz Poziom 0?”."
            )),
        ],
    ),
]

# Historie z serduszkami (demo_likes): pierwsza dostaje najwięcej. Wszystkie mają ≥ 2 zatwierdzone fragmenty.
LIKED_STORIES = [
    STARTERS[AgeGroup.middle].title,
    "Kot detektyw i zaginiona skarpetka",
    STARTERS[AgeGroup.teen].title,
    "Mecz o wszystko",
    "Kosmiczna kanapka",
]


def check_dataset() -> list[str]:
    """Spójność zestawu: cytaty dosłowne, sztafeta, limity długości. Pusta lista = OK."""
    problems: list[str] = []
    for st in DEMO_STORIES:
        previous: list[str] = []  # zatwierdzone fragmenty przed bieżącym
        last_human: str | None = None
        for i, seg in enumerate(st.segments, 1):
            where = f"{st.title!r} #{i}"
            if i == 1 and seg.author is not None:
                problems.append(f"{where}: historię zaczyna narrator AI")
            if seg.author is None:
                if seg.review or seg.rejected_by:
                    problems.append(f"{where}: fragment AI bez oceny/odrzucenia")
            else:
                age = DEMO_USERS[seg.author][1]
                if not 15 <= len(seg.text) <= MAX_LEN[age]:
                    problems.append(f"{where}: długość {len(seg.text)} poza limitem dla {age}")
                if seg.author == last_human:
                    problems.append(f"{where}: {seg.author} pisze dwa razy z rzędu (sztafeta)")
                if seg.rejected_by is None and seg.review is None:
                    problems.append(f"{where}: brak oceny zrozumienia")
                if seg.review and seg.review.evidence not in "\n\n".join(previous):
                    problems.append(f"{where}: cytat nie jest dosłownym fragmentem wcześniejszego tekstu")
            if seg.approved:
                previous.append(seg.text)
                if seg.author is not None:
                    last_human = seg.author
    smok = next(s for s in DEMO_STORIES if s.title == STARTERS[AgeGroup.young].title)
    if smok.title in LIKED_STORIES:
        problems.append("Smok: bez polubień — zostaje w stanie startowym")
    titles = {s.title: s for s in DEMO_STORIES}
    for t in LIKED_STORIES:
        if t not in titles or sum(x.approved for x in titles[t].segments) < 2:
            problems.append(f"{t!r}: polubiona historia musi istnieć i mieć ≥ 2 zatwierdzone fragmenty")
    if any(s.author for s in smok.segments):
        problems.append("Smok: w historii z demo nie może być jeszcze fragmentów dzieci")
    return problems
