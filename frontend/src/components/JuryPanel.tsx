import { JuryResetButton } from "./jury";

/** Panel trybu jury: konkretny scenariusz testu + reset bazy do historii demo. */
export default function JuryPanel() {
  return (
    <section className="mt-4 rounded-3xl bg-card p-4 ring-2 ring-ink">
      <h2 className="font-black">Tryb jury: co sprawdzić w 3 minuty</h2>
      <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm">
        <li>
          Otwórz <b>„Smok, który bał się ciemności”</b> i dopisz 1–2 zdania nawiązujące do zgasłej latarenki albo
          pukania. Zobaczysz ocenę zrozumienia, podświetlone zdanie z historii, na którym AI ją oparło, i od razu
          fragment dopisany przez narratora.
        </li>
        <li>
          Dopisz coś niezwiązanego, np. o zakupach. Fragment wejdzie, ale z niską oceną i wskazówką, do czego warto
          było nawiązać — trafi też na listę w zakładce <b>Poprawki</b>.
        </li>
        <li>
          Wpisz przekleństwo albo numer telefonu i adres. Moderacja zatrzyma tekst i wyjaśni dlaczego; nikt inny go
          nie zobaczy.
        </li>
        <li>
          Zacznij własną historię (<b>Nowa historia</b>) i pisz ją dalej — swoje historie znajdziesz pod filtrem{" "}
          <b>Moje</b>. Otwórz apkę w drugiej karcie jako inna osoba: nowe fragmenty pojawiają się na żywo.
        </li>
      </ol>
      <p className="mt-3 text-xs font-semibold text-muted">
        Wszystko działa na prawdziwym modelu (Groq). Reset przywraca historie startowe.
      </p>
      <JuryResetButton big />
    </section>
  );
}
