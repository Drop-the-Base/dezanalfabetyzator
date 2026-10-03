import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type LikeState, type Story } from "../lib/api";
import { AGE_LABELS, etapy } from "../lib/brand";
import { useJury } from "../lib/jury";
import { useLive } from "../lib/live";
import { useSession } from "../lib/session";
import { AvatarStack, LikeButton, Mascot, TabBar, TopBar, timeAgo } from "../components/ui";
import JuryPanel from "../components/JuryPanel";

export default function Feed() {
  const { user } = useSession();
  const { jury } = useJury();
  const [stories, setStories] = useState<Story[] | null>(null);
  const [onlyMine, setOnlyMine] = useState(false);
  const [fresh, setFresh] = useState<Set<number>>(new Set());

  useEffect(() => {
    api.stories().then(setStories).catch(() => setStories([]));
  }, []);

  useLive(({ stories: changed }) => {
    if (!changed.length) return;
    setStories((prev) => {
      const map = new Map((prev ?? []).map((s) => [s.id, s]));
      changed.forEach((s) => map.set(s.id, s));
      return [...map.values()].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    });
    setFresh((f) => new Set([...f, ...changed.map((s) => s.id)]));
  });

  const setLike = (id: number, l: LikeState) =>
    setStories((prev) => prev && prev.map((s) => (s.id === id ? { ...s, ...l } : s)));

  const list = (stories ?? []).filter((s) => !onlyMine || s.age_group === user?.age_group);

  return (
    <>
      <TopBar />
      <TabBar />
      <main className="mx-auto max-w-xl px-4 pb-32 pt-4">
        <section className="flex items-center gap-3 rounded-3xl bg-ai-soft p-4">
          <Mascot size={52} />
          <p className="text-sm font-semibold text-ai">
            Cześć, {user?.nick}! Wybierz historię, <b>przeczytaj ją uważnie</b> i dopisz ciąg dalszy. Ja sprawdzę, czy
            wszystko się łączy.
          </p>
        </section>

        {jury && <JuryPanel />}

        <div className="mt-5 flex gap-2">
          {[
            [false, "Wszystkie"],
            [true, `Dla mnie (${user ? AGE_LABELS[user.age_group] : ""})`],
          ].map(([val, label]) => (
            <button
              key={String(val)}
              onClick={() => setOnlyMine(val as boolean)}
              className={`rounded-full px-4 py-1.5 text-sm font-extrabold ${
                onlyMine === val ? "bg-ink text-white" : "bg-card ring-2 ring-line"
              }`}
            >
              {label as string}
            </button>
          ))}
        </div>

        <ul className="mt-4 flex flex-col gap-3">
          {stories === null &&
            [0, 1, 2].map((i) => <li key={i} className="h-28 animate-pulse rounded-3xl bg-card" />)}
          {stories && list.length === 0 && (
            <li className="rounded-3xl bg-card p-6 text-center font-semibold text-muted">
              Jeszcze nie ma historii. Zacznij pierwszą!
            </li>
          )}
          {list.map((s) => {
            const myTurn = s.last_human_author_id !== user?.id;
            return (
              <li key={s.id}>
                <Link
                  to={`/historia/${s.id}`}
                  className={`block rounded-3xl bg-card p-4 shadow-sm ring-1 ring-line transition active:scale-[0.99] ${
                    fresh.has(s.id) ? "animate-glow" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-lg font-black leading-tight">{s.title}</h2>
                    <span className="shrink-0 rounded-full bg-paper px-2 py-0.5 text-xs font-bold text-muted">
                      {AGE_LABELS[s.age_group]}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AvatarStack authors={s.authors} />
                      <span className="text-sm font-semibold text-muted">
                        {etapy(s.segment_count)} ·{" "}
                        {timeAgo(s.updated_at)}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <LikeButton
                        storyId={s.id}
                        count={s.like_count}
                        liked={s.liked_by_me}
                        onChange={(l) => setLike(s.id, l)}
                        size="sm"
                      />
                      {myTurn ? (
                        <span className="rounded-full bg-baton px-3 py-1 text-xs font-extrabold text-white">
                          Twoja kolej →
                        </span>
                      ) : (
                        <span className="rounded-full bg-paper px-3 py-1 text-xs font-bold text-muted">Czekasz…</span>
                      )}
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </main>

      <div className="fixed inset-x-0 bottom-0 z-10 bg-gradient-to-t from-paper via-paper to-transparent px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-6">
        <Link
          to="/nowa"
          className="mx-auto flex max-w-xl items-center justify-center gap-2 rounded-2xl bg-baton py-4 text-lg font-extrabold text-white shadow-[0_4px_0_var(--color-baton-dark)]"
        >
          ✏️ Nowa historia
        </Link>
      </div>
    </>
  );
}
