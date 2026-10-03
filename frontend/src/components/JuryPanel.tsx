import { JuryResetButton } from "./jury";

/** Panel trybu jury: krótka instrukcja + reset bazy do historii demo. */
export default function JuryPanel() {
  return (
    <section className="mt-4 rounded-3xl bg-card p-4 ring-2 ring-line">
      <h2 className="font-black">⚖️ Tryb jury — jak testować</h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm font-semibold text-muted">
        <li>Wybierz historię z listy (każda grupa wiekowa ma swoje) i przeczytaj ją.</li>
        <li>Dopisz ciąg dalszy — Sowa AI oceni, czy zrozumiałeś(-aś) tekst, i pokaże cytat.</li>
        <li>
          Spróbuj tekstu zupełnie nie na temat albo niegrzecznego — AI życzliwie go zatrzyma. Fragment, który ma choć
          trochę sensu, wchodzi do historii i trafia do „Do poprawienia”.
        </li>
        <li>„🔥 Na topie” — najpopularniejsze historie tylko do czytania i dawania serduszek.</li>
        <li>„✍️ Poprawki” — zaznacz kawałek cudzego tekstu, wpisz poprawkę, a AI oceni, czy pasuje do historii.</li>
        <li>„🔄 Reset” (na górze każdej strony) przywraca historie demo.</li>
      </ul>
      <JuryResetButton big />
    </section>
  );
}
