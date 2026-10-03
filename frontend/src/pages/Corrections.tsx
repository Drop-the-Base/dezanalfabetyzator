import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Correction, type ToFix } from "../lib/api";
import { useLive } from "../lib/live";
import { Avatar, Mascot, TabBar, TopBar, timeAgo } from "../components/ui";
import { CorrectionCard } from "../components/corrections";

/** Zakładka „Poprawki” — ostatnie poprawki z werdyktami AI + fragmenty do poprawienia (#32). */
export default function Corrections() {
  const [recent, setRecent] = useState<Correction[] | null>(null);
  const [toFix, setToFix] = useState<ToFix[] | null>(null);

  const load = () => {
    api.corrections().then(setRecent).catch(() => setRecent([]));
    api.correctionsToFix().then(setToFix).catch(() => setToFix([]));
  };
  useEffect(load, []);
  useLive(load); // nowe fragmenty / przyjęte poprawki — odśwież listy

  return (
    <>
      <TopBar />
      <TabBar />
      <main className="mx-auto max-w-xl px-4 pb-10 pt-4">
        <section className="flex items-center gap-3 rounded-3xl bg-ai-soft p-4">
          <Mascot size={52} />
          <p className="text-sm font-semibold text-ai">
            Coś się nie zgadza w czyjejś historii? <b>Zaznacz ten kawałek</b> w historii i zaproponuj poprawkę. Sprawdzę,
            czy pasuje do tego, co było wcześniej.
          </p>
        </section>

        <h2 className="mt-6 text-lg font-black">🔎 Do poprawienia</h2>
        <p className="text-sm text-muted">Fragmenty, które tylko częściowo łączą się z historią.</p>
        <ul className="mt-3 flex flex-col gap-3">
          {toFix === null && [0, 1].map((i) => <li key={i} className="h-24 animate-pulse rounded-3xl bg-card" />)}
          {toFix?.length === 0 && (
            <li className="rounded-3xl bg-card p-5 text-center font-semibold text-muted">
              Wszystko wygląda spójnie. Brawo, czytelnicy! ✨
            </li>
          )}
          {toFix?.map((t) => (
            <li key={t.segment.id}>
              <Link
                to={`/historia/${t.story_id}#seg-${t.segment.id}`}
                className="block rounded-3xl bg-card p-4 shadow-sm ring-1 ring-line transition active:scale-[0.99]"
              >
                <div className="flex items-center gap-2">
                  <Avatar author={t.segment.author} size="sm" />
                  <span className="min-w-0 flex-1 truncate text-sm font-extrabold">{t.story_title}</span>
                  <span className="shrink-0 rounded-full bg-mid-soft px-2 py-0.5 text-xs font-black text-mid">
                    {t.segment.comprehension_score}%
                  </span>
                </div>
                <p className="story-text mt-2 line-clamp-3 text-sm">{t.segment.text}</p>
                <p className="mt-2 text-right text-sm font-extrabold text-baton">Popraw →</p>
              </Link>
            </li>
          ))}
        </ul>

        <h2 className="mt-8 text-lg font-black">✍️ Ostatnie poprawki</h2>
        <ul className="mt-3 flex flex-col gap-3">
          {recent === null && [0, 1].map((i) => <li key={i} className="h-28 animate-pulse rounded-3xl bg-card" />)}
          {recent?.length === 0 && (
            <li className="rounded-3xl bg-card p-5 text-center font-semibold text-muted">
              Jeszcze nikt nic nie poprawiał. Bądź pierwszy!
            </li>
          )}
          {recent?.map((c) => (
            <li key={c.id}>
              <Link to={`/historia/${c.story_id}#seg-${c.segment_id}`} className="mb-1 flex gap-2 px-2 text-xs font-bold text-muted">
                <span className="min-w-0 flex-1 truncate">📖 {c.story_title}</span>
                <span className="shrink-0">{timeAgo(c.created_at)}</span>
              </Link>
              <CorrectionCard c={c} />
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
