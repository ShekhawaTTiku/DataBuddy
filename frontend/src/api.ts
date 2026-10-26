import type { Session } from "./types";
const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const key = "databuddy.session.v1";
let token: string | null = null;
try {
  token = sessionStorage.getItem(key);
} catch {
  /* Memory-only fallback. */
}
let initial: Promise<Session> | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${base}/api${path}`, {
      ...options,
      headers,
      signal: AbortSignal.timeout(110_000),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "The server is unavailable or waking up. Wait a moment, then try again.",
      0,
    );
  }
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new ApiError(
      response.ok
        ? "The API address is not configured correctly. Check the frontend API URL."
        : "The server is unavailable or waking up. Wait a moment, then try again.",
      response.ok ? 502 : response.status,
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new ApiError(
      typeof data.detail === "string"
        ? data.detail
        : "Check your input and try again.",
      response.status,
    );
  return data as T;
}
export function startSession(fresh = false): Promise<Session> {
  if (fresh) {
    token = null;
    initial = null;
    try {
      sessionStorage.removeItem(key);
    } catch {
      /* Optional storage. */
    }
  }
  if (!initial)
    initial = (async () => {
      if (token) return request<Session>("/session");
      const data = await request<Session & { token: string }>("/session", {
        method: "POST",
      });
      token = data.token;
      try {
        sessionStorage.setItem(key, token);
      } catch {
        /* Optional storage. */
      }
      return data;
    })().finally(() => {
      initial = null;
    });
  return initial;
}
export const readSession = () => request<Session>("/session");
