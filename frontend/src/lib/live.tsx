/**
 * Live updates przez polling (Vercel nie obsługuje WebSocketów).
 * Jeden poller na aplikację; ekrany subskrybują zdarzenia.
 * Interfejs (subscribe) pozwala później podmienić transport na Pusher/Ably bez zmian w ekranach.
 */
import { createContext, useContext, useEffect, useRef, type ReactNode } from "react";
import { api, type Segment, type Story } from "./api";

const INTERVAL_MS = 1500;

export interface LiveEvent {
  stories: Story[];
  segments: Segment[];
}

type Listener = (e: LiveEvent) => void;

interface LiveCtx {
  subscribe: (fn: Listener) => () => void;
}

const Ctx = createContext<LiveCtx | null>(null);

export function LiveProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const listeners = useRef(new Set<Listener>());
  const cursor = useRef<string | null>(null);
  const seen = useRef(new Map<number, string>()); // segment id → updated_at (deduplikacja)

  useEffect(() => {
    if (!enabled) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      if (stop) return;
      if (document.visibilityState === "visible") {
        try {
          const u = await api.updates(cursor.current);
          const first = cursor.current === null;
          cursor.current = u.cursor;
          const fresh = u.segments.filter((s) => seen.current.get(s.id) !== s.updated_at);
          fresh.forEach((s) => seen.current.set(s.id, s.updated_at));
          if (!first && (fresh.length || u.stories.length)) {
            listeners.current.forEach((fn) => fn({ stories: u.stories, segments: fresh }));
          }
        } catch {
          /* chwilowy brak sieci — spróbujemy za chwilę */
        }
      }
      timer = setTimeout(tick, INTERVAL_MS);
    };
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [enabled]);

  const subscribe = (fn: Listener) => {
    listeners.current.add(fn);
    return () => listeners.current.delete(fn);
  };

  return <Ctx.Provider value={{ subscribe }}>{children}</Ctx.Provider>;
}

export function useLive(fn: Listener) {
  const ctx = useContext(Ctx);
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => ctx?.subscribe((e) => ref.current(e)), [ctx]);
}
