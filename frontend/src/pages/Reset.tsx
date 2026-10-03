import { useState } from "react";
import { api } from "../lib/api";
import { Button, Mascot } from "../components/ui";

/** Ukryta strona /reset (nie ma do niej linku): przywraca bazę do historii demo przed prezentacją. */
export default function Reset() {
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const reset = async () => {
    setBusy(true);
    setError("");
    try {
      await api.resetDemo(pin);
      window.location.assign("/"); // świeże dane na każdej zakładce
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-5 text-center">
      <Mascot size={64} />
      <h1 className="text-2xl font-black">Reset demo</h1>
      <p className="text-sm font-semibold text-muted">Przywraca historie startowe. Wszystkie zmiany zostaną usunięte.</p>
      <form
        className="flex w-full flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          reset();
        }}
      >
        <input
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          inputMode="numeric"
          placeholder="PIN (jeśli serwer wymaga)"
          autoComplete="off"
          className="rounded-2xl border-2 border-line bg-card px-4 py-3 text-center text-lg font-bold outline-none focus:border-baton"
        />
        {error && <p className="rounded-xl bg-bad-soft px-4 py-2 font-bold text-bad">{error}</p>}
        <Button type="submit" disabled={busy}>
          {busy ? "Resetuję…" : "Resetuj bazę demo"}
        </Button>
      </form>
      <a href="/" className="text-sm font-bold text-muted underline">
        Wróć do aplikacji
      </a>
    </main>
  );
}
