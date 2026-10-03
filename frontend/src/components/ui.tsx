import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { api, type Author, type LikeState } from "../lib/api";
import { APP_NAME, AVATARS } from "../lib/brand";
import { useSession } from "../lib/session";
import { JuryResetButton, JuryToggle } from "./jury";

/** Sowa — głos AI w aplikacji. */
export function Mascot({ size = 56, thinking = false }: { size?: number; thinking?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden className={thinking ? "animate-bounce" : ""}>
      <ellipse cx="32" cy="38" rx="22" ry="22" fill="#7c3aed" />
      <ellipse cx="32" cy="44" rx="13" ry="13" fill="#ede9fe" />
      <path d="M12 22 L20 30 L14 32 Z M52 22 L44 30 L50 32 Z" fill="#6d28d9" />
      <circle cx="23" cy="32" r="9" fill="#fff" />
      <circle cx="41" cy="32" r="9" fill="#fff" />
      {thinking ? (
        <>
          <path d="M18 32 q5 -4 10 0" stroke="#1f2937" strokeWidth="2.5" fill="none" strokeLinecap="round" />
          <path d="M36 32 q5 -4 10 0" stroke="#1f2937" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="24" cy="32" r="4" fill="#1f2937" />
          <circle cx="40" cy="32" r="4" fill="#1f2937" />
          <circle cx="25.5" cy="30.5" r="1.3" fill="#fff" />
          <circle cx="41.5" cy="30.5" r="1.3" fill="#fff" />
        </>
      )}
      <path d="M29 38 L32 43 L35 38 Z" fill="#f97316" />
    </svg>
  );
}

export function Avatar({ author, size = "md" }: { author: Pick<Author, "avatar" | "is_ai">; size?: "sm" | "md" | "lg" }) {
  const dims = { sm: "h-7 w-7 text-base", md: "h-10 w-10 text-xl", lg: "h-14 w-14 text-3xl" }[size];
  if (author.is_ai) {
    return (
      <span className={`${dims} inline-grid place-items-center rounded-full bg-ai-soft ring-2 ring-white`}>
        <Mascot size={size === "lg" ? 44 : size === "md" ? 32 : 22} />
      </span>
    );
  }
  return (
    <span className={`${dims} inline-grid place-items-center rounded-full bg-baton-soft ring-2 ring-white`}>
      {AVATARS[author.avatar] ?? "🙂"}
    </span>
  );
}

export function AvatarStack({ authors, max = 5 }: { authors: Author[]; max?: number }) {
  const shown = authors.slice(0, max);
  return (
    <div className="flex -space-x-2">
      {shown.map((a, i) => (
        <Avatar key={`${a.id}-${i}`} author={a} size="sm" />
      ))}
      {authors.length > max && (
        <span className="grid h-7 w-7 place-items-center rounded-full bg-line text-xs font-bold ring-2 ring-white">
          +{authors.length - max}
        </span>
      )}
    </div>
  );
}

export function TopBar({ back, title }: { back?: string; title?: string }) {
  const { user, logout } = useSession();
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-xl items-center gap-3 px-4 py-3">
        {back ? (
          <Link to={back} className="-ml-2 rounded-full p-2 text-2xl leading-none hover:bg-baton-soft" aria-label="Wróć">
            ←
          </Link>
        ) : (
          <span aria-hidden>
            <Mascot size={32} />
          </span>
        )}
        <h1 className="min-w-0 flex-1 truncate text-lg font-black tracking-tight">{title ?? APP_NAME}</h1>
        {user && <JuryResetButton />}
        <JuryToggle />
        {user && (
          <button
            onClick={logout}
            className="flex shrink-0 items-center gap-2 rounded-full bg-card p-1 text-sm font-bold shadow-sm sm:pr-3"
            title={`${user.nick} — wyloguj`}
          >
            <Avatar author={{ avatar: user.avatar, is_ai: false }} size="sm" />
            <span className="hidden sm:inline">{user.nick}</span>
          </button>
        )}
      </div>
    </header>
  );
}

const TABS = [
  { to: "/", label: "Historie" },
  { to: "/na-topie", label: "Na topie" },
  { to: "/poprawki", label: "Poprawki" },
];

/** Główne zakładki — pod TopBar na ekranach list. */
export function TabBar() {
  return (
    <nav className="border-b border-line bg-paper">
      <div className="mx-auto grid max-w-xl grid-cols-3 gap-1 px-4 py-2">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end
            className={({ isActive }) =>
              `rounded-xl py-2 text-center text-sm font-extrabold ${isActive ? "bg-ink text-white" : "bg-card ring-1 ring-line"}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "ai" }) {
  const styles = {
    primary: "bg-baton text-white shadow-[0_4px_0_var(--color-baton-dark)] active:translate-y-[2px] active:shadow-[0_2px_0_var(--color-baton-dark)]",
    ai: "bg-ai text-white shadow-[0_4px_0_#5b21b6] active:translate-y-[2px] active:shadow-[0_2px_0_#5b21b6]",
    ghost: "bg-card text-ink border-2 border-line",
  }[variant];
  return (
    <button
      {...props}
      className={`rounded-2xl px-5 py-3 text-base font-extrabold transition disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

/**
 * Serduszko z licznikiem. Kontrolowane: rodzic trzyma stan historii, a przycisk
 * zmienia go od razu (optymistycznie) i potem poprawia odpowiedzią serwera.
 * Działa też wewnątrz <Link> (blokuje przejście do historii).
 */
export function LikeButton({
  storyId,
  count,
  liked,
  onChange,
  size = "md",
}: {
  storyId: number;
  count: number;
  liked: boolean;
  onChange: (s: LikeState) => void;
  size?: "sm" | "md";
}) {
  const busy = useRef(false);
  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (busy.current) return;
    busy.current = true;
    const next = !liked;
    onChange({ like_count: Math.max(0, count + (next ? 1 : -1)), liked_by_me: next });
    try {
      onChange(await (next ? api.like(storyId) : api.unlike(storyId)));
    } catch {
      onChange({ like_count: count, liked_by_me: liked });
    } finally {
      busy.current = false;
    }
  };
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={liked}
      aria-label={liked ? "Już nie lubię tej historii" : "Lubię tę historię"}
      className={`inline-flex shrink-0 items-center gap-1 rounded-full font-extrabold transition active:scale-90 ${
        size === "sm" ? "px-2.5 py-1 text-sm" : "px-3 py-1.5 text-base"
      } ${liked ? "bg-bad-soft text-bad" : "bg-paper text-muted ring-1 ring-line"}`}
    >
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden className={liked ? "animate-pop" : ""}><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.2 5.2 3 1.6-1.8 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z" fill={liked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinejoin="round" /></svg>
      {count}
    </button>
  );
}

/* --- Toasty („Kuba przejął pałeczkę!”) --- */
interface Toast {
  id: number;
  text: string;
  icon: ReactNode;
}
const ToastCtx = createContext<(text: string, icon?: ReactNode) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, icon: ReactNode = null) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-2), { id, text, icon }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-16 z-50 flex flex-col items-center gap-2 px-4">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-slide-up flex max-w-sm items-center gap-2 rounded-2xl bg-ink px-4 py-3 text-sm font-bold text-white shadow-lg"
          >
            {t.icon && <span className="shrink-0">{t.icon}</span>}
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);

export function timeAgo(iso: string): string {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
  if (s < 60) return "przed chwilą";
  if (s < 3600) return `${Math.floor(s / 60)} min temu`;
  if (s < 86400) return `${Math.floor(s / 3600)} godz. temu`;
  return `${Math.floor(s / 86400)} dni temu`;
}
