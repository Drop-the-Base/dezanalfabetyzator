import { useState } from "react";
import type { AgeGroup } from "../lib/api";
import { AGE_LABELS, APP_NAME, AVATARS, TAGLINE } from "../lib/brand";
import { useSession } from "../lib/session";
import { Button, Mascot } from "../components/ui";

const DEMO: { nick: string; avatar: string; age: AgeGroup }[] = [
  { nick: "Zosia", avatar: "rabbit", age: "7-10" },
  { nick: "Maja", avatar: "cat", age: "11-14" },
  { nick: "Kuba", avatar: "fox", age: "15-18" },
];

export default function Login() {
  const { login } = useSession();
  const [nick, setNick] = useState("");
  const [avatar, setAvatar] = useState("fox");
  const [age, setAge] = useState<AgeGroup>("7-10");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (n = nick, a = avatar, g = age) => {
    if (n.trim().length < 2) return setError("Wpisz imię albo ksywkę (min. 2 litery).");
    setBusy(true);
    setError("");
    try {
      await login(n.trim(), a, g);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-8 pt-[max(2rem,env(safe-area-inset-top))]">
      <div className="animate-pop flex flex-col items-center text-center">
        <div className="relative">
          <Mascot size={88} />
          <span className="absolute -right-3 -top-1 rotate-12 text-3xl">🏃</span>
        </div>
        <h1 className="mt-3 text-4xl font-black tracking-tight">{APP_NAME}</h1>
        <p className="mt-1 font-semibold text-muted">{TAGLINE}</p>
      </div>

      <form
        className="mt-8 flex flex-col gap-6"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className="flex flex-col gap-2">
          <span className="font-extrabold">Jak masz na imię?</span>
          <input
            value={nick}
            onChange={(e) => setNick(e.target.value)}
            maxLength={24}
            placeholder="np. Zosia albo Smoczy_Mistrz"
            autoComplete="off"
            className="rounded-2xl border-2 border-line bg-card px-4 py-3 text-lg font-bold outline-none focus:border-baton"
          />
          <span className="text-xs text-muted">Tylko imię lub ksywka — bez nazwiska.</span>
        </label>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-extrabold">Wybierz swojego biegacza</legend>
          <div className="grid grid-cols-4 gap-3">
            {Object.entries(AVATARS).map(([key, emoji]) => (
              <button
                type="button"
                key={key}
                onClick={() => setAvatar(key)}
                aria-pressed={avatar === key}
                className={`aspect-square rounded-2xl text-4xl transition ${
                  avatar === key ? "scale-105 bg-baton-soft ring-4 ring-baton" : "bg-card ring-2 ring-line"
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 font-extrabold">Ile masz lat?</legend>
          <div className="grid grid-cols-3 gap-2">
            {(Object.keys(AGE_LABELS) as AgeGroup[]).map((g) => (
              <button
                type="button"
                key={g}
                onClick={() => setAge(g)}
                aria-pressed={age === g}
                className={`rounded-2xl py-3 font-extrabold transition ${
                  age === g ? "bg-ink text-white" : "bg-card ring-2 ring-line"
                }`}
              >
                {AGE_LABELS[g]}
              </button>
            ))}
          </div>
        </fieldset>

        {error && <p className="rounded-xl bg-bad-soft px-4 py-2 font-bold text-bad">{error}</p>}

        <Button type="submit" disabled={busy} className="py-4 text-lg">
          {busy ? "Wchodzę…" : "Wbiegam do sztafety! 🏁"}
        </Button>
      </form>

      <div className="mt-8 text-center">
        <p className="text-xs font-bold uppercase tracking-wider text-muted">Szybkie demo</p>
        <div className="mt-2 flex justify-center gap-2">
          {DEMO.map((d) => (
            <button
              key={d.nick}
              onClick={() => submit(d.nick, d.avatar, d.age)}
              disabled={busy}
              className="rounded-full bg-card px-3 py-1.5 text-sm font-bold ring-2 ring-line"
            >
              {AVATARS[d.avatar]} {d.nick} · {d.age}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
