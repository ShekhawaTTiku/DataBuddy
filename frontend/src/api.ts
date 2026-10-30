import type { Session, ResponseUpdate } from "./types";
import { readEvents } from "./streaming";
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

export async function watchResponse(
  id: string,
  receive: (update: ResponseUpdate) => void,
  signal: AbortSignal,
): Promise<void> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal.addEventListener("abort", abort, { once: true });
  if (signal.aborted) abort();
  let timer: ReturnType<typeof setTimeout>;
  const activity = () => {
    clearTimeout(timer);
    timer = setTimeout(abort, 35_000);
  };
  activity();
  try {
    const headers = new Headers({ Accept: "text/event-stream" });
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(
      `${base}/api/jobs/${encodeURIComponent(id)}/events`,
      {
        headers,
        signal: controller.signal,
        cache: "no-store",
      },
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new ApiError(
        typeof data.detail === "string"
          ? data.detail
          : "The response connection is unavailable.",
        response.status,
      );
    }
    if (
      !response.body ||
      !response.headers.get("content-type")?.includes("text/event-stream")
    ) {
      throw new ApiError("The server could not open the response stream.", 502);
    }
    await readEvents(
      response.body,
      (event, data) => {
        if (event === "update") {
          const update = JSON.parse(data) as ResponseUpdate;
          if (
            update.id !== id ||
            typeof update.answer !== "string" ||
            typeof update.version !== "number" ||
            !update.job
          ) {
            throw new Error("Invalid response update.");
          }
          receive(update);
        }
      },
      activity,
    );
  } finally {
    clearTimeout(timer!);
    signal.removeEventListener("abort", abort);
    controller.abort();
  }
}
