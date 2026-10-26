import { readTurnEvents } from "@/lib/sse";
import type {
  Health,
  Intent,
  Learner,
  LearnerProfile,
  NewSession,
  Progress,
  Session,
  SessionSummary,
  TurnEvent,
} from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

/** A failed API call. `status` is 0 when the API could not be reached at all. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "The tutor API could not be reached.");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Not JSON: keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  return (await (await send(path, init)).json()) as T;
}

const id = (value: string) => encodeURIComponent(value);

export const api = {
  health: () => json<Health>("/health"),
  createLearner: (profile: LearnerProfile) =>
    json<Learner>("/learners", { method: "POST", body: JSON.stringify(profile) }),
  getLearner: (learnerId: string) => json<Learner>(`/learners/${id(learnerId)}`),
  updateLearner: (learnerId: string, profile: LearnerProfile) =>
    json<Learner>(`/learners/${id(learnerId)}`, {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  listSessions: (learnerId: string) =>
    json<SessionSummary[]>(`/learners/${id(learnerId)}/sessions`),
  progress: (learnerId: string) => json<Progress>(`/learners/${id(learnerId)}/progress`),
  createSession: (body: NewSession) =>
    json<Session>("/sessions", { method: "POST", body: JSON.stringify(body) }),
  getSession: (sessionId: string) => json<Session>(`/sessions/${id(sessionId)}`),

  /** Send a message and yield the tutor's reply as it streams in. */
  async *streamMessage(
    sessionId: string,
    content: string,
    intent: Intent = "auto",
    signal?: AbortSignal,
  ): AsyncGenerator<TurnEvent> {
    const response = await send(`/sessions/${id(sessionId)}/messages/stream`, {
      method: "POST",
      body: JSON.stringify({ content, intent }),
      headers: { Accept: "text/event-stream" },
      signal,
    });
    if (!response.body) throw new ApiError(0, "The response has no body to stream.");
    yield* readTurnEvents(response.body);
  },
};
