export type AgeGroup = "7-10" | "11-14" | "15-18";

export interface User {
  id: number;
  nick: string;
  avatar: string;
  age_group: AgeGroup;
}

export interface Author {
  id: number | null;
  nick: string;
  avatar: string;
  is_ai: boolean;
}

export interface Segment {
  id: number;
  story_id: number;
  position: number;
  text: string;
  status: "approved" | "rejected";
  comprehension_score: number | null;
  author: Author;
  created_at: string;
  updated_at: string;
}

export interface Story {
  id: number;
  title: string;
  theme: string;
  age_group: AgeGroup;
  segment_count: number;
  authors: Author[];
  last_author_id: number | null;
  last_human_author_id: number | null;
  like_count: number;
  liked_by_me: boolean;
  created_at: string;
  updated_at: string;
}

export interface LikeState {
  like_count: number;
  liked_by_me: boolean;
}

export interface StoryDetail extends Story {
  segments: Segment[];
}

export interface Review {
  id: number;
  segment_id: number;
  kind: string;
  verdict: "understood" | "partially" | "not_understood" | string;
  score: number | null;
  reason: string;
  evidence: string;
  strengths: string;
  categories: string[];
  model: string;
  created_at: string;
}

/** Poprawka niespójności w cudzym fragmencie + werdykt AI (#32). */
export interface Correction {
  id: number;
  segment_id: number;
  story_id: number;
  story_title: string;
  author: Author;
  segment_author: Author;
  original: string;
  proposed: string;
  reason: string;
  status: "pending" | "accepted" | "rejected";
  ai_feedback: string;
  evidence: string;
  model: string;
  created_at: string;
}

export interface CorrectionResult {
  correction: Correction;
  segment: Segment;
  blocked_by_moderation: boolean;
}

export interface ToFix {
  story_id: number;
  story_title: string;
  segment: Segment;
}

export interface SubmitResult {
  segment: Segment | null;
  moderation: { verdict: "ok" | "reject"; reason: string; categories: string[] };
  comprehension: Review | null;
  ai_segment: Segment | null;
  story_id: number | null;
}

export interface Updates {
  cursor: string;
  stories: Story[];
  segments: Segment[];
  my_segments: Segment[];
}

const TOKEN_KEY = "sztafeta.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* tryb prywatny — trudno */
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    let msg = "Coś poszło nie tak. Spróbuj jeszcze raz.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = "Sprawdź, czy wszystko jest dobrze wypełnione.";
    } catch {
      /* brak JSON */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  login: (nick: string, avatar: string, age_group: AgeGroup) =>
    post<{ token: string; user: User }>("/auth/demo", { nick, avatar, age_group }),
  me: () => request<User>("/auth/me"),
  themes: () => request<string[]>("/themes"),
  stories: () => request<Story[]>("/stories"),
  story: (id: number) => request<StoryDetail>(`/stories/${id}`),
  trending: () => request<Story[]>("/stories/trending"),
  like: (id: number) => request<LikeState>(`/stories/${id}/like`, { method: "POST" }),
  unlike: (id: number) => request<LikeState>(`/stories/${id}/like`, { method: "DELETE" }),
  proposeCorrection: (segmentId: number, original: string, proposed: string, reason: string) =>
    post<CorrectionResult>(`/segments/${segmentId}/corrections`, { original, proposed, reason }),
  corrections: () => request<Correction[]>("/corrections"),
  correctionsToFix: () => request<ToFix[]>("/corrections/to-fix"),
  storyCorrections: (storyId: number) => request<Correction[]>(`/stories/${storyId}/corrections`),
  segmentCorrections: (segmentId: number) => request<Correction[]>(`/segments/${segmentId}/corrections`),
  createStory: (title: string, text: string) => post<SubmitResult>("/stories", { title, text }),
  createAIStory: (theme: string) => post<Story>("/stories/ai", { theme }),
  addSegment: (storyId: number, text: string) => post<SubmitResult>(`/stories/${storyId}/segments`, { text }),
  updates: (since: string | null) =>
    request<Updates>(`/updates${since ? `?since=${encodeURIComponent(since)}` : ""}`),
};
