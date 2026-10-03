import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

/** Tryb jury: przełącznik na górze strony (domyślnie włączony) — podpowiedzi i dane logowania jury. */
const KEY = "sztafeta.jury";

interface JuryCtx {
  jury: boolean;
  setJury: (on: boolean) => void;
}

const Ctx = createContext<JuryCtx | null>(null);

function stored(): boolean {
  try {
    return localStorage.getItem(KEY) !== "0";
  } catch {
    return true;
  }
}

export function JuryProvider({ children }: { children: ReactNode }) {
  const [jury, setState] = useState(stored);
  const setJury = useCallback((on: boolean) => {
    setState(on);
    try {
      localStorage.setItem(KEY, on ? "1" : "0");
    } catch {
      /* tryb prywatny — trudno */
    }
  }, []);
  return <Ctx.Provider value={{ jury, setJury }}>{children}</Ctx.Provider>;
}

export function useJury() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useJury poza JuryProvider");
  return ctx;
}
