import type { AgeGroup } from "./api";

export const APP_NAME = "Sztafeta Słów";
export const TAGLINE = "Przeczytaj. Zrozum. Przekaż pałeczkę.";

export const AVATARS: Record<string, string> = {
  fox: "🦊",
  owl: "🦉",
  cat: "🐱",
  bear: "🐻",
  frog: "🐸",
  panda: "🐼",
  rabbit: "🐰",
  dragon: "🐲",
};

export const AGE_LABELS: Record<AgeGroup, string> = {
  "7-10": "7–10 lat",
  "11-14": "11–14 lat",
  "15-18": "15+",
};

export const MAX_LEN: Record<AgeGroup, number> = { "7-10": 400, "11-14": 800, "15-18": 1200 };

/** Odmiana „etap”: 1 etap, 2–4 etapy, 5+ etapów (12–14 etapów). */
export function etapy(n: number): string {
  if (n === 1) return "1 etap";
  const d = n % 10;
  const t = n % 100;
  return `${n} ${d >= 2 && d <= 4 && (t < 12 || t > 14) ? "etapy" : "etapów"}`;
}
