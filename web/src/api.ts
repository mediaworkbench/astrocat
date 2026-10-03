/** Typed client for the AstroCat API (concept §10.1). Cookies carry the session. */

import type { Language } from "./i18n";

export type Gender = "neutral" | "feminine" | "masculine";
export type CategoryName = "love" | "work" | "energy" | "mood";
export const CATEGORIES: CategoryName[] = ["love", "work", "energy", "mood"];

export interface Birth {
  date: string;
  time: string | null;
  place_name: string;
  place_id: number | null;
  latitude: number;
  longitude: number;
  timezone: string;
  utc_offset_override: number | null;
}

export interface Me {
  username: string;
  display_name: string;
  language: Language;
  grammatical_gender: Gender;
  timezone: string;
  birth: Birth | null;
  onboarding_complete: boolean;
}

export interface Place {
  id: number;
  name: string;
  country_code: string;
  latitude: number;
  longitude: number;
  timezone: string;
  population: number;
}

export interface ManualPlace {
  name: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface BirthUpdate {
  date: string;
  time: string | null;
  place_id?: number;
  place?: ManualPlace;
}

export interface Factor {
  id: string;
  kind: "aspect" | "placement";
  transit: string;
  aspect: string | null;
  natal: string | null;
  house: number;
  nature: "harmonious" | "tense" | "neutral";
  exact_at: string | null;
  background: boolean;
}

export interface Today {
  date: string;
  language: Language;
  status: "ok" | "fallback";
  reading: {
    headline: string;
    summary: string;
    sections: Record<CategoryName, string>;
    advice: string;
  };
  day: { moon_sign: string; moon_phase: string; overall_score: number; mira_pose: string };
  categories: Record<CategoryName, { score: number }>;
  birth_time_known: boolean;
  sun_sign: string;
  factors: Factor[];
  generated_at: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number, // 0 = network error
    message: string,
    readonly retryAfter?: number,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network error");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* not JSON */
    }
    const retry = Number(response.headers.get("retry-after"));
    throw new ApiError(response.status, detail, Number.isFinite(retry) && retry > 0 ? retry : undefined);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  me: () => request<Me>("GET", "/api/me"),
  login: (username: string, password: string) => request<Me>("POST", "/api/auth/login", { username, password }),
  logout: () => request<void>("POST", "/api/auth/logout"),
  updateSettings: (changes: Partial<Pick<Me, "display_name" | "language" | "grammatical_gender" | "timezone">>) =>
    request<Me>("PUT", "/api/me/settings", changes),
  updateBirth: (birth: BirthUpdate) => request<Me>("PUT", "/api/me/birth", birth),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("POST", "/api/me/password", { current_password, new_password }),
  searchPlaces: (q: string) => request<Place[]>("GET", `/api/places?q=${encodeURIComponent(q)}`),
  today: () => request<Today>("GET", "/api/today"),
};
