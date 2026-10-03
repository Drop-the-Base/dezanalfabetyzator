import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type LikeState, type Story } from "../lib/api";
import { AGE_LABELS, etapy } from "../lib/brand";
import { JuryHint } from "../components/jury";
import { AvatarStack, LikeButton, Mascot, TabBar, TopBar, timeAgo } from "../components/ui";

const REFRESH_MS = 5000;
const MEDALS = ["🥇", "🥈", "🥉"];

/** Zakładka „Na topie” — historie z największą liczbą serduszek (świeże mają premię). */
export default function Trending() {
  const [stories, setStories] = useState<Story[] | null>(null);

  // Polubienia nie zmieniają kolejności na liście historii, więc ranking odświeżamy sami:
  // co kilka sekund (gdy karta jest widoczna) i po powrocie do aplikacji.
  useEffect(() => {
    let alive = true;
    const load = () => {
      if (document.visibilityState !== "visible") return;
      api
        .trending()
        .then((s) => alive && setStories(s))
        .catch(() => alive && setStories((prev) => prev ?? []));
    };
    load();
    const timer = setInterval(load, REFRESH_MS);
    window.addEventListener("focus", load);
    document.addEventListener("visibilitychange", load);
    return () => {
      alive = false;
      clearInterval(timer);
      window.removeEventListener("focus", load);
      document.removeEventListener("visibilitychange", load);
    };
  }, []);

  const setLike = (id: number, l: LikeState) =>
    setStories((prev) => prev && prev.map((s) => (s.id === id ? { ...s, ...l } : s)));

  return (
    <>
      <TopBar />
      <TabBar />
      <main className="mx-auto max-w-xl px-4 pb-10 pt-4">
        <section className="flex items-center gap-3 rounded-3xl bg-ai-soft p-4">
          <Mascot size={52} />
          <p className="text-sm font-semibold text-ai">
            Te historie zbierają najwięcej serduszek! Przeczytaj je i kliknij 🤍, jeśli Ci się podobają.
          </p>
        </section>
        <JuryHint>
          Ranking: serduszka z premią za świeżość. Historie „na topie” są <b>tylko do czytania i oceniania</b> — nie
          można ich dopisywać, ale można zaznaczyć niespójny fragment i zaproponować poprawkę.
        </JuryHint>

        <ol className="mt-4 flex flex-col gap-3">
          {stories === null &&
            [0, 1, 2].map((i) => <li key={i} className="h-24 animate-pulse rounded-3xl bg-card" />)}
          {stories && stories.length === 0 && (
            <li className="flex flex-col items-center gap-3 rounded-3xl bg-card p-6 text-center ring-1 ring-line">
              <Mascot size={64} />
              <p className="font-bold">Jeszcze nic nie jest na topie.</p>
              <p className="text-sm font-semibold text-muted">
                Przeczytaj historie i daj serduszko tym, które Ci się podobają — wtedy pojawią się tutaj!
              </p>
              <Link to="/" className="rounded-full bg-ink px-4 py-2 text-sm font-extrabold text-white">
                📚 Do historii
              </Link>
            </li>
          )}
          {stories?.map((s, i) => (
            <li key={s.id}>
              <Link
                to={`/historia/${s.id}?czytaj=1`}
                className={`flex items-center gap-3 rounded-3xl bg-card p-4 shadow-sm ring-1 transition active:scale-[0.99] ${
                  i < 3 ? "ring-2 ring-baton" : "ring-line"
                }`}
              >
                <span
                  className={`flex w-9 shrink-0 justify-center font-black ${i < 3 ? "text-3xl" : "text-lg text-muted"}`}
                  aria-label={`Miejsce ${i + 1}`}
                >
                  {MEDALS[i] ?? `${i + 1}.`}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="truncate text-lg font-black leading-tight">{s.title}</h2>
                  <div className="mt-2 flex items-center gap-2">
                    <AvatarStack authors={s.authors} max={3} />
                    <span className="truncate text-xs font-semibold text-muted">
                      {etapy(s.segment_count)} · {AGE_LABELS[s.age_group]} · {timeAgo(s.updated_at)}
                    </span>
                  </div>
                </div>
                <LikeButton
                  storyId={s.id}
                  count={s.like_count}
                  liked={s.liked_by_me}
                  onChange={(l) => setLike(s.id, l)}
                  size="sm"
                />
              </Link>
            </li>
          ))}
        </ol>
      </main>
    </>
  );
}
