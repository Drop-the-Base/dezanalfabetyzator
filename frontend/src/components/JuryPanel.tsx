import { useState } from "react";
import { api } from "../lib/api";
import { Button, useToast } from "./ui";

/** Panel trybu jury: krótka instrukcja + reset bazy do historii demo (PIN z RESET_PIN). */
export default function JuryPanel({ onReset }: { onReset: () => void }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const reset = async () => {
    if (!pin.trim()) return setError("Wpisz PIN.");
    setBusy(true);
    setError("");
    try {
      const res = await api.resetDemo(pin.trim());
      // Reset usuwa też konta — podpisany token odtworzy je przy kolejnym zapytaniu.
      onReset();
      setOpen(false);
      setPin("");
      toast(`Demo zresetowane: ${res.counts.stories ?? 0} historii gotowych do czytania.`, "🔄");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mt-4 rounded-3xl bg-card p-4 ring-2 ring-line">
      <h2 className="font-black">⚖️ Tryb jury — jak testować</h2>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm font-semibold text-muted">
        <li>Wybierz historię z listy (każda grupa wiekowa ma swoje) i przeczytaj ją.</li>
        <li>Dopisz ciąg dalszy — Sowa AI oceni, czy zrozumiałeś(-aś) tekst, i pokaże cytat.</li>
        <li>Spróbuj tekstu nie na temat albo niegrzecznego — zobacz, jak AI życzliwie go zatrzyma.</li>
        <li>„🔥 Na topie” — najpopularniejsze historie tylko do czytania i dawania serduszek.</li>
        <li>„✍️ Poprawki” — zaznacz kawałek cudzego tekstu, wpisz poprawkę, a AI oceni, czy pasuje do historii.</li>
      </ul>

      {!open ? (
        <Button variant="ghost" className="mt-3 w-full" onClick={() => setOpen(true)}>
          🔄 Resetuj demo
        </Button>
      ) : (
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            reset();
          }}
        >
          <label className="text-sm font-bold" htmlFor="jury-pin">
            PIN do resetu (wszystkie zmiany zostaną usunięte)
          </label>
          <div className="flex gap-2">
            <input
              id="jury-pin"
              type="password"
              inputMode="numeric"
              autoComplete="off"
              autoFocus
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="min-w-0 flex-1 rounded-2xl border-2 border-line bg-paper px-4 py-2 font-bold outline-none focus:border-baton"
            />
            <Button type="submit" disabled={busy} className="py-2">
              {busy ? "Resetuję…" : "Resetuj"}
            </Button>
          </div>
          {error && <p className="rounded-xl bg-bad-soft px-3 py-2 text-sm font-bold text-bad">{error}</p>}
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              setError("");
            }}
            className="self-start text-sm font-bold text-muted underline"
          >
            Anuluj
          </button>
        </form>
      )}
    </section>
  );
}
