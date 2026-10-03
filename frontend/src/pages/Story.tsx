import { Fragment, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError, type Review, type StoryDetail, type SubmitResult } from "../lib/api";
import { AGE_LABELS, MAX_LEN, etapy } from "../lib/brand";
import { useLive } from "../lib/live";
import { useSession } from "../lib/session";
import { Avatar, Button, Mascot, TopBar, useToast } from "../components/ui";

/** Znajduje cytat w tekście mimo różnic w białych znakach. Zwraca [start, end] albo null. */
function findQuote(text: string, quote: string): [number, number] | null {
  if (!quote) return null;
  const words = quote.trim().split(/\s+/).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const m = new RegExp(words.join("\\s+"), "i").exec(text);
  return m ? [m.index, m.index + m[0].length] : null;
}

function Highlighted({ text, quote, markRef }: { text: string; quote: string; markRef?: React.Ref<HTMLElement> }) {
  const range = findQuote(text, quote);
  if (!range) return <>{text}</>;
  return (
    <>
      {text.slice(0, range[0])}
      <mark ref={markRef} className="evidence">
        {text.slice(range[0], range[1])}
      </mark>
      {text.slice(range[1])}
    </>
  );
}

const VERDICT = {
  understood: { label: "Przeczytane ze zrozumieniem!", stars: 3, tone: "bg-good-soft text-good" },
  partially: { label: "Prawie! Coś umknęło", stars: 2, tone: "bg-mid-soft text-mid" },
  not_understood: { label: "Hmm, to się nie łączy", stars: 1, tone: "bg-bad-soft text-bad" },
} as const;

function ResultCard({ result, onShowEvidence, onClose }: { result: SubmitResult; onShowEvidence: () => void; onClose: () => void }) {
  if (result.moderation.verdict === "reject") {
    return (
      <div className="animate-pop rounded-3xl bg-bad-soft p-5">
        <div className="flex items-start gap-3">
          <Mascot size={52} />
          <div>
            <p className="font-black text-bad">Ups, tego nie możemy opublikować</p>
            <p className="mt-1 font-semibold">{result.moderation.reason}</p>
          </div>
        </div>
        <Button variant="ghost" className="mt-4 w-full" onClick={onClose}>
          Poprawię swój tekst
        </Button>
      </div>
    );
  }
  const c: Review | null = result.comprehension;
  const v = c ? VERDICT[c.verdict as keyof typeof VERDICT] ?? VERDICT.partially : null;
  return (
    <div className="animate-pop rounded-3xl bg-card p-5 shadow-lg ring-1 ring-line">
      <div className="flex items-start gap-3">
        <Mascot size={52} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-extrabold text-good">✓ Pałeczka przekazana! Twój fragment jest w historii.</p>
          {c && v && (
            <>
              <div className={`mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-black ${v.tone}`}>
                <span>{"★".repeat(v.stars)}{"☆".repeat(3 - v.stars)}</span>
                {v.label}
              </div>
              <p className="mt-2 font-semibold">{c.reason}</p>
              {c.strengths && <p className="mt-1 text-sm text-muted">👍 {c.strengths}</p>}
            </>
          )}
        </div>
      </div>
      {c?.evidence && (
        <button
          onClick={onShowEvidence}
          className="mt-4 w-full rounded-2xl bg-mid-soft p-3 text-left text-sm font-semibold"
        >
          <span className="block text-xs font-black uppercase tracking-wide text-mid">Na tym oparłam ocenę</span>
          „{c.evidence}”
          <span className="mt-1 block text-xs font-extrabold text-mid">Pokaż w historii ↑</span>
        </button>
      )}
      <Button variant="ghost" className="mt-3 w-full" onClick={onClose}>
        Super, zamknij
      </Button>
    </div>
  );
}

export default function Story() {
  const { id } = useParams();
  const storyId = Number(id);
  const { user } = useSession();
  const toast = useToast();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [error, setError] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [quote, setQuote] = useState("");
  const [newIds, setNewIds] = useState<Set<number>>(new Set());
  const markRef = useRef<HTMLElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.story(storyId).then(setStory).catch((e) => setError((e as Error).message));
  }, [storyId]);

  useLive(({ segments }) => {
    const mine = segments.filter((s) => s.story_id === storyId);
    if (!mine.length) return;
    setStory((prev) => {
      if (!prev) return prev;
      const have = new Set(prev.segments.map((s) => s.id));
      const add = mine.filter((s) => !have.has(s.id));
      if (!add.length) return prev;
      add.filter((s) => s.author.id !== user?.id).forEach((s) => toast(`${s.author.nick} przejął(-ęła) pałeczkę!`, "🏃"));
      setNewIds((n) => new Set([...n, ...add.map((s) => s.id)]));
      const segments = [...prev.segments, ...add].sort((a, b) => a.position - b.position);
      const authors = [...prev.authors];
      add.forEach((s) => {
        if (!authors.some((a) => a.id === s.author.id)) authors.push(s.author);
      });
      return { ...prev, segments, authors, segment_count: segments.length, last_author_id: segments[segments.length - 1].author.id };
    });
  });

  const showEvidence = () => {
    setTimeout(() => markRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
  };

  const submit = async () => {
    if (!story) return;
    setBusy(true);
    setError("");
    try {
      const r = await api.addSegment(story.id, text);
      setResult(r);
      if (r.moderation.verdict === "ok" && r.segment) {
        setText("");
        setQuote(r.comprehension?.evidence ?? "");
        const seg = r.segment;
        setStory((prev) =>
          prev && !prev.segments.some((s) => s.id === seg.id)
            ? {
                ...prev,
                segments: [...prev.segments, seg],
                segment_count: prev.segment_count + 1,
                last_author_id: seg.author.id,
                authors: prev.authors.some((a) => a.id === seg.author.id) ? prev.authors : [...prev.authors, seg.author],
              }
            : prev && { ...prev, last_author_id: seg.author.id },
        );
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Brak połączenia. Spróbuj jeszcze raz.");
    } finally {
      setBusy(false);
    }
  };

  if (!story) {
    return (
      <>
        <TopBar back="/" title="Historia" />
        <main className="mx-auto max-w-xl p-4">
          {error ? <p className="font-bold text-bad">{error}</p> : <div className="h-64 animate-pulse rounded-3xl bg-card" />}
        </main>
      </>
    );
  }

  const max = user ? MAX_LEN[user.age_group] : 800;
  const myTurn = story.last_author_id !== user?.id;
  // Cytat podświetlamy tylko we fragmentach PRZED najnowszym fragmentem użytkownika
  const lastMine = result?.segment?.id;

  return (
    <div data-age={user?.age_group}>
      <TopBar back="/" title={story.title} />
      <main className="mx-auto max-w-xl px-4 pb-8 pt-4">
        <div className="mb-4 flex items-center gap-2 text-sm font-bold text-muted">
          <span className="rounded-full bg-card px-2 py-0.5 ring-1 ring-line">{AGE_LABELS[story.age_group]}</span>
          <span>{etapy(story.segment_count)} sztafety</span>
        </div>

        <ol className="flex flex-col gap-4">
          {story.segments.map((s, i) => (
            <Fragment key={s.id}>
              {i > 0 && (
                <li aria-hidden className="-my-2 flex items-center justify-center text-xs font-black uppercase tracking-widest text-baton">
                  ↓ pałeczka ↓
                </li>
              )}
              <li
                className={`rounded-3xl p-4 ${s.author.is_ai ? "bg-ai-soft" : "bg-card ring-1 ring-line"} ${
                  newIds.has(s.id) ? "animate-slide-up" : ""
                }`}
              >
                <div className="mb-2 flex items-center gap-2">
                  <Avatar author={s.author} size="sm" />
                  <span className={`text-sm font-extrabold ${s.author.is_ai ? "text-ai" : ""}`}>{s.author.nick}</span>
                  {s.author.id === user?.id && s.comprehension_score !== null && (
                    <span className="ml-auto rounded-full bg-paper px-2 py-0.5 text-xs font-bold text-muted">
                      zrozumienie: {s.comprehension_score}%
                    </span>
                  )}
                </div>
                <p className="story-text whitespace-pre-line">
                  {s.id === lastMine ? s.text : <Highlighted text={s.text} quote={quote} markRef={markRef} />}
                </p>
              </li>
            </Fragment>
          ))}
        </ol>
        <div ref={endRef} />

        <section className="mt-6">
          {result && (
            <ResultCard
              result={result}
              onShowEvidence={showEvidence}
              onClose={() => {
                setResult(null);
                setQuote("");
              }}
            />
          )}

          {!result &&
            (busy ? (
              <div className="flex items-center gap-3 rounded-3xl bg-ai-soft p-5">
                <Mascot size={52} thinking />
                <p className="font-bold text-ai">Czytam Twój fragment i sprawdzam, czy pasuje do historii…</p>
              </div>
            ) : myTurn ? (
              <div className="rounded-3xl bg-card p-4 shadow-sm ring-2 ring-baton">
                <label htmlFor="cont" className="flex items-center gap-2 font-black">
                  <span className="text-xl">🏃</span> Twoja kolej! Co było dalej?
                </label>
                <p className="mt-1 text-sm text-muted">Najpierw przeczytaj uważnie całą historię — sprawdzę, czy do niej nawiązujesz.</p>
                <textarea
                  id="cont"
                  value={text}
                  onChange={(e) => setText(e.target.value.slice(0, max))}
                  rows={5}
                  placeholder="Nagle…"
                  className="story-text mt-3 w-full resize-none rounded-2xl border-2 border-line bg-paper p-3 outline-none focus:border-baton"
                />
                <div className="mt-1 flex justify-between text-xs font-bold text-muted">
                  <span>{error && <span className="text-bad">{error}</span>}</span>
                  <span>
                    {text.length}/{max}
                  </span>
                </div>
                <Button className="mt-3 w-full" disabled={text.trim().length < 15} onClick={submit}>
                  Przekaż pałeczkę →
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-3xl bg-card p-5 ring-1 ring-line">
                <span className="text-3xl">⏳</span>
                <p className="font-semibold text-muted">
                  Twój fragment jest ostatni. Poczekaj, aż ktoś inny przejmie pałeczkę — zobaczysz to tutaj na żywo!
                </p>
              </div>
            ))}
        </section>
      </main>
    </div>
  );
}
