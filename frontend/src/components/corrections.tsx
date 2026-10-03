/** Poprawki niespójności (#32): zaznaczanie tekstu, arkusz z propozycją, werdykt AI, znaczek „poprawione”. */
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type Correction, type CorrectionResult, type Segment } from "../lib/api";
import { Avatar, Button, Mascot } from "./ui";

/** Dokładny kawałek `text` odpowiadający zaznaczeniu (zaznaczenie może mieć inne białe znaki). */
export function exactInText(text: string, selected: string): string | null {
  const q = selected.trim();
  if (!q) return null;
  if (text.includes(q)) return q;
  const words = q.split(/\s+/).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const m = new RegExp(words.join("\\s+")).exec(text);
  return m ? m[0] : null;
}

export interface SegmentSelection {
  segmentId: number;
  text: string;
}

/**
 * Śledzi zaznaczenie tekstu wewnątrz elementów z `data-correctable={segment.id}`.
 * Działa też na telefonie (selectionchange). Po odznaczeniu czeka chwilę, żeby przycisk zdążył przyjąć kliknięcie.
 */
export function useSegmentSelection(): [SegmentSelection | null, () => void] {
  const [sel, setSel] = useState<SegmentSelection | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    const onChange = () => {
      const s = window.getSelection();
      const text = s?.toString().trim() ?? "";
      const node = s?.anchorNode;
      const el = (node instanceof Element ? node : node?.parentElement)?.closest<HTMLElement>("[data-correctable]");
      clearTimeout(timer.current);
      if (text && el && el.contains(s?.focusNode ?? null)) {
        setSel({ segmentId: Number(el.dataset.correctable), text });
      } else {
        timer.current = setTimeout(() => setSel(null), 400);
      }
    };
    document.addEventListener("selectionchange", onChange);
    return () => {
      document.removeEventListener("selectionchange", onChange);
      clearTimeout(timer.current);
    };
  }, []);
  return [sel, () => setSel(null)];
}

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Znaczek „poprawione” + podgląd oryginał → poprawka. */
export function CorrectedBadge({ corrections }: { corrections: Correction[] }) {
  const [open, setOpen] = useState(false);
  const accepted = corrections.filter((c) => c.status === "accepted");
  if (!accepted.length) return null;
  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded-full bg-good-soft px-2 py-0.5 text-xs font-extrabold text-good"
        aria-expanded={open}
      >
        poprawione{accepted.length > 1 ? ` ×${accepted.length}` : ""}
      </button>
      {open && (
        <ul className="order-last mt-2 flex w-full flex-col gap-2">
          {accepted.map((c) => (
            <li key={c.id} className="rounded-2xl bg-good-soft p-3 text-sm">
              <CorrectionDiff c={c} />
              <p className="mt-1 text-xs font-bold text-muted">poprawka: {c.author.nick}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function CorrectionDiff({ c }: { c: Pick<Correction, "original" | "proposed"> }) {
  return (
    <p className="font-semibold">
      <del className="text-bad decoration-2">{c.original}</del>
      <span className="mx-1 font-black text-muted">→</span>
      <ins className="text-good no-underline">{c.proposed}</ins>
    </p>
  );
}

type Step = "pick" | "edit" | "busy" | "result";

/** Dolny arkusz: wybór kawałka → propozycja → werdykt sowy. */
export function CorrectionSheet({
  segment,
  initial,
  onClose,
  onResult,
  onShowEvidence,
}: {
  segment: Segment;
  initial: string;
  onClose: () => void;
  onResult: (r: CorrectionResult) => void;
  onShowEvidence: (evidence: string) => void;
}) {
  const start = exactInText(segment.text, initial) ?? "";
  const [step, setStep] = useState<Step>(start ? "edit" : "pick");
  const [original, setOriginal] = useState(start);
  const [proposed, setProposed] = useState(start);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<CorrectionResult | null>(null);
  const pickRef = useRef<HTMLParagraphElement>(null);

  const choose = (text: string) => {
    const exact = exactInText(segment.text, text);
    if (!exact) {
      setError("Nie mogę znaleźć tego kawałka we fragmencie. Wybierz zdanie poniżej.");
      return;
    }
    setOriginal(exact);
    setProposed(exact);
    setError("");
    setStep("edit");
  };

  const chooseSelection = () => {
    const s = window.getSelection();
    if (s && pickRef.current?.contains(s.anchorNode)) choose(s.toString());
    else setError("Najpierw zaznacz palcem albo myszką kawałek tekstu powyżej.");
  };

  const submit = async () => {
    setStep("busy");
    setError("");
    try {
      const r = await api.proposeCorrection(segment.id, original, proposed.trim(), reason.trim());
      setResult(r);
      setStep("result");
      onResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Brak połączenia. Spróbuj jeszcze raz.");
      setStep("edit");
    }
  };

  const c = result?.correction;

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/40" onClick={onClose}>
      <div
        role="dialog"
        aria-modal
        aria-label="Zgłoś niespójność"
        onClick={(e) => e.stopPropagation()}
        className="animate-slide-up max-h-[90dvh] w-full max-w-xl overflow-y-auto rounded-t-3xl bg-paper p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-2xl"
      >
        <div className="mx-auto mb-3 h-1.5 w-12 rounded-full bg-line" aria-hidden />
        <div className="mb-3 flex items-center gap-2">
          <h2 className="flex-1 text-lg font-black">To chyba nie jest spójne</h2>
          <button onClick={onClose} className="rounded-full p-2 text-xl leading-none hover:bg-line" aria-label="Zamknij">
            ✕
          </button>
        </div>

        {step === "pick" && (
          <>
            <p className="text-sm font-semibold text-muted">
              Który kawałek nie pasuje do wcześniejszej części historii? Stuknij zdanie albo zaznacz dokładny kawałek.
            </p>
            <p ref={pickRef} className="story-text mt-3 select-text rounded-2xl bg-card p-3 ring-1 ring-line">
              {segment.text}
            </p>
            <Button variant="ghost" className="mt-2 w-full text-sm" onClick={chooseSelection}>
              Użyj zaznaczonego kawałka
            </Button>
            <div className="mt-3 flex flex-col gap-2">
              {sentences(segment.text).map((s, i) => (
                <button
                  key={i}
                  onClick={() => choose(s)}
                  className="rounded-2xl bg-card p-3 text-left text-sm font-semibold ring-1 ring-line active:bg-baton-soft"
                >
                  {s}
                </button>
              ))}
            </div>
            {error && <p className="mt-2 text-sm font-bold text-bad">{error}</p>}
          </>
        )}

        {step === "edit" && (
          <>
            <p className="text-xs font-black uppercase tracking-wide text-muted">Zaznaczony kawałek</p>
            <p className="mt-1 rounded-2xl bg-mid-soft p-3 text-sm font-semibold">„{original}”</p>
            <button onClick={() => setStep("pick")} className="mt-1 text-xs font-extrabold text-mid">
              Wybierz inny kawałek
            </button>
            <label htmlFor="corr-proposed" className="mt-3 block font-black">
              Jak powinno być?
            </label>
            <textarea
              id="corr-proposed"
              value={proposed}
              onChange={(e) => setProposed(e.target.value.slice(0, 600))}
              rows={3}
              className="story-text mt-1 w-full resize-none rounded-2xl border-2 border-line bg-card p-3 outline-none focus:border-baton"
            />
            <label htmlFor="corr-reason" className="mt-2 block text-sm font-bold">
              Dlaczego? <span className="font-semibold text-muted">(nie musisz)</span>
            </label>
            <input
              id="corr-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value.slice(0, 300))}
              placeholder="np. wcześniej smok był zielony"
              className="mt-1 w-full rounded-2xl border-2 border-line bg-card p-3 text-sm outline-none focus:border-baton"
            />
            {error && <p className="mt-2 text-sm font-bold text-bad">{error}</p>}
            <Button
              variant="ai"
              className="mt-3 w-full"
              disabled={!proposed.trim() || proposed.trim() === original.trim()}
              onClick={submit}
            >
              Sprawdź moją poprawkę
            </Button>
          </>
        )}

        {step === "busy" && (
          <div className="flex items-center gap-3 rounded-3xl bg-ai-soft p-5">
            <Mascot size={52} thinking />
            <p className="font-bold text-ai">Czytam historię od początku i sprawdzam, czy Twoja poprawka pasuje…</p>
          </div>
        )}

        {step === "result" && c && (
          <div className={`animate-pop rounded-3xl p-5 ${c.status === "accepted" ? "bg-good-soft" : "bg-mid-soft"}`}>
            <div className="flex items-start gap-3">
              <Mascot size={52} />
              <div className="min-w-0 flex-1">
                <p className={`font-black ${c.status === "accepted" ? "text-good" : "text-mid"}`}>
                  {c.status === "accepted"
                    ? "✓ Poprawka przyjęta! Fragment jest już zmieniony."
                    : result?.blocked_by_moderation
                      ? "Ups, tej poprawki nie możemy przyjąć"
                      : "Tym razem nie zmieniamy"}
                </p>
                <p className="mt-1 font-semibold">{c.ai_feedback}</p>
              </div>
            </div>
            <div className="mt-3 rounded-2xl bg-card p-3 text-sm">
              <CorrectionDiff c={c} />
            </div>
            {c.evidence && (
              <button
                onClick={() => onShowEvidence(c.evidence)}
                className="mt-3 w-full rounded-2xl bg-card p-3 text-left text-sm font-semibold"
              >
                <span className="block text-xs font-black uppercase tracking-wide text-mid">Na tym oparłam ocenę</span>
                „{c.evidence}”
                <span className="mt-1 block text-xs font-extrabold text-mid">Pokaż w historii ↑</span>
              </button>
            )}
            {c.status === "accepted" ? (
              <Button variant="ghost" className="mt-3 w-full" onClick={onClose}>
                Super, zamknij
              </Button>
            ) : (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Button variant="ghost" onClick={onClose}>
                  Zamknij
                </Button>
                <Button onClick={() => setStep("edit")}>Spróbuj jeszcze raz</Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Mała karta poprawki — zakładka „Poprawki”. */
export function CorrectionCard({ c }: { c: Correction }) {
  const ok = c.status === "accepted";
  return (
    <div className="rounded-3xl bg-card p-4 shadow-sm ring-1 ring-line">
      <div className="flex items-center gap-2">
        <Avatar author={c.author} size="sm" />
        <span className="min-w-0 flex-1 truncate text-sm font-extrabold">
          {c.author.nick} <span className="font-semibold text-muted">poprawia: {c.segment_author.nick}</span>
        </span>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-black ${ok ? "bg-good-soft text-good" : "bg-mid-soft text-mid"}`}
        >
          {ok ? "✓ przyjęta" : "✗ nieprzyjęta"}
        </span>
      </div>
      <div className="mt-2 text-sm">
        <CorrectionDiff c={c} />
      </div>
      {c.ai_feedback && (
        <p className="mt-2 flex items-start gap-2 text-sm text-ai">
          <span className="font-semibold">{c.ai_feedback}</span>
        </p>
      )}
    </div>
  );
}
