import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { MAX_LEN } from "../lib/brand";
import { useSession } from "../lib/session";
import { Button, Mascot, TopBar } from "../components/ui";

const THEME_ICONS: Record<string, string> = {
  smoki: "🐉",
  kosmos: "🚀",
  detektyw: "🔍",
  "piłka nożna": "⚽",
  "gry komputerowe": "🎮",
  szkoła: "🏫",
  zwierzęta: "🐾",
  "podróż w czasie": "⏳",
};

export default function NewStory() {
  const { user } = useSession();
  const nav = useNavigate();
  const [mode, setMode] = useState<"ai" | "own">("ai");
  const [themes, setThemes] = useState<string[]>([]);
  const [theme, setTheme] = useState("");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.themes().then(setThemes).catch(() => {});
  }, []);

  const startAI = async () => {
    setBusy(true);
    setError("");
    try {
      const s = await api.createAIStory(theme);
      nav(`/historia/${s.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const startOwn = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await api.createStory(title, text);
      if (r.moderation.verdict === "reject" || !r.story_id) {
        setError(r.moderation.reason);
        setBusy(false);
        return;
      }
      nav(`/historia/${r.story_id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const max = user ? MAX_LEN[user.age_group] : 800;

  return (
    <div data-age={user?.age_group}>
      <TopBar back="/" title="Nowa historia" />
      <main className="mx-auto max-w-xl px-4 pb-10 pt-4">
        <div className="grid grid-cols-2 gap-2 rounded-2xl bg-card p-1 ring-1 ring-line">
          {(
            [
              ["ai", "🦉 Zacznie Sowa AI"],
              ["own", "✏️ Zaczynam sam(a)"],
            ] as const
          ).map(([m, label]) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-xl py-2.5 font-extrabold ${mode === m ? (m === "ai" ? "bg-ai text-white" : "bg-baton text-white") : ""}`}
            >
              {label}
            </button>
          ))}
        </div>

        {busy && mode === "ai" ? (
          <div className="mt-8 flex flex-col items-center gap-3 text-center">
            <Mascot size={96} thinking />
            <p className="text-lg font-black text-ai">Wymyślam początek historii…</p>
          </div>
        ) : mode === "ai" ? (
          <section className="mt-6">
            <p className="font-extrabold">O czym ma być historia?</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {themes.map((t) => (
                <button
                  key={t}
                  onClick={() => setTheme(t === theme ? "" : t)}
                  aria-pressed={theme === t}
                  className={`flex items-center gap-2 rounded-2xl px-3 py-3 text-left font-bold transition ${
                    theme === t ? "bg-ai-soft ring-4 ring-ai" : "bg-card ring-2 ring-line"
                  }`}
                >
                  <span className="text-2xl">{THEME_ICONS[t] ?? "✨"}</span>
                  {t}
                </button>
              ))}
            </div>
            <input
              value={themes.includes(theme) ? "" : theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="…albo wpisz własny temat"
              maxLength={60}
              className="mt-3 w-full rounded-2xl border-2 border-line bg-card px-4 py-3 font-bold outline-none focus:border-ai"
            />
            <p className="mt-3 text-sm text-muted">
              Sowa napisze pierwszy fragment dopasowany do Twojego wieku. Potem pałeczkę przejmą inni.
            </p>
            {error && <p className="mt-3 rounded-xl bg-bad-soft px-4 py-2 font-bold text-bad">{error}</p>}
            <Button variant="ai" className="mt-5 w-full py-4 text-lg" onClick={startAI}>
              {theme ? `Zacznij historię: ${theme}` : "Zaskocz mnie!"}
            </Button>
          </section>
        ) : (
          <section className="mt-6 flex flex-col gap-3">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Tytuł"
              maxLength={120}
              className="rounded-2xl border-2 border-line bg-card px-4 py-3 text-lg font-black outline-none focus:border-baton"
            />
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, max))}
              rows={7}
              placeholder="Dawno, dawno temu…"
              className="story-text resize-none rounded-2xl border-2 border-line bg-card p-3 outline-none focus:border-baton"
            />
            <p className="text-right text-xs font-bold text-muted">
              {text.length}/{max}
            </p>
            <p className="rounded-2xl bg-baton-soft p-3 text-sm font-semibold">
              💡 Wprowadź bohatera z imieniem i zakończ w ciekawym momencie — tak, żeby następna osoba miała do czego
              nawiązać.
            </p>
            {error && <p className="rounded-xl bg-bad-soft px-4 py-2 font-bold text-bad">{error}</p>}
            <Button className="w-full py-4 text-lg" disabled={busy || title.trim().length < 2 || text.trim().length < 15} onClick={startOwn}>
              {busy ? "Sprawdzam…" : "Startuj sztafetę! 🏁"}
            </Button>
          </section>
        )}
      </main>
    </div>
  );
}
