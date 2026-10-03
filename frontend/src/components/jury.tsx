import { useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { useJury } from "../lib/jury";

/** Przełącznik „Tryb jury” — na górze strony (logowanie i TopBar). */
export function JuryToggle({ label = "⚖️ Jury", onToggle }: { label?: string; onToggle?: (on: boolean) => void }) {
  const { jury, setJury } = useJury();
  return (
    <button
      type="button"
      role="switch"
      aria-checked={jury}
      onClick={() => (onToggle ?? setJury)(!jury)}
      className={`flex shrink-0 items-center gap-2 rounded-full py-1 pl-2 pr-1 text-xs font-extrabold ring-1 transition ${
        jury ? "bg-ink text-white ring-ink" : "bg-card text-muted ring-line"
      }`}
      title="Tryb jury: podpowiedzi i gotowe dane logowania"
    >
      {label}
      <span className={`relative h-5 w-9 rounded-full transition ${jury ? "bg-baton" : "bg-line"}`}>
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${jury ? "left-[18px]" : "left-0.5"}`}
        />
      </span>
    </button>
  );
}

/** Reset bazy do historii demo — widoczny tylko w trybie jury. Potwierdzenie w miejscu (bez okienek przeglądarki). */
export function JuryResetButton({ big = false }: { big?: boolean }) {
  const { jury } = useJury();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!jury) return null;

  const reset = async () => {
    setBusy(true);
    setError("");
    try {
      await api.resetDemo("");
      window.location.assign("/"); // świeże dane na każdej zakładce
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <div className={big ? "mt-3" : "relative"}>
      <button
        type="button"
        onClick={() => setConfirm((c) => !c)}
        className={
          big
            ? "w-full rounded-2xl bg-paper py-3 font-extrabold ring-2 ring-line"
            : "shrink-0 rounded-full bg-card px-2.5 py-1 text-xs font-extrabold ring-1 ring-line"
        }
        title="Resetuj bazę do historii demo"
      >
        🔄 {big ? "Resetuj bazę demo" : "Reset"}
      </button>
      {confirm && (
        <div
          className={`${
            big ? "mt-2" : "absolute right-0 top-full z-30 mt-2 w-64 shadow-lg"
          } rounded-2xl bg-card p-3 text-sm ring-2 ring-line`}
        >
          <p className="font-bold">Przywrócić historie demo? Wszystkie zmiany zostaną usunięte.</p>
          {error && <p className="mt-2 rounded-xl bg-bad-soft px-2 py-1 font-bold text-bad">{error}</p>}
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={reset}
              className="flex-1 rounded-xl bg-ink py-2 font-extrabold text-white disabled:opacity-60"
            >
              {busy ? "Resetuję…" : "Tak, resetuj"}
            </button>
            <button
              type="button"
              onClick={() => setConfirm(false)}
              className="flex-1 rounded-xl bg-paper py-2 font-extrabold ring-1 ring-line"
            >
              Anuluj
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Dodatkowa podpowiedź widoczna tylko w trybie jury. */
export function JuryHint({ children }: { children: ReactNode }) {
  const { jury } = useJury();
  if (!jury) return null;
  return (
    <aside className="mt-4 flex gap-2 rounded-2xl border-2 border-dashed border-ink/30 bg-card px-4 py-3 text-sm font-semibold">
      <span aria-hidden>⚖️</span>
      <div>{children}</div>
    </aside>
  );
}
