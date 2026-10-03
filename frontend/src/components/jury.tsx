import type { ReactNode } from "react";
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
