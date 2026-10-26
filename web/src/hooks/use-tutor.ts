"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useI18n } from "@/components/i18n-provider";
import { api, ApiError } from "@/lib/api";
import { learnerCache } from "@/lib/profile";
import type {
  GradeResult,
  Health,
  Intent,
  Learner,
  LearnerProfile,
  NewSession,
  Progress,
  Route,
  Session,
  SessionSummary,
} from "@/lib/types";

export type Phase = "loading" | "unreachable" | "onboarding" | "ready";

export interface UIMessage {
  id: string;
  role: "student" | "tutor";
  content: string;
  route?: Route;
  streaming?: boolean;
  failed?: boolean;
}

export interface HintState {
  level: number;
  max: number;
}

function toMessages(session: Session): UIMessage[] {
  return session.messages.map((message, index) => ({
    id: `${session.session_id}-${index}`,
    role: message.role,
    content: message.content,
  }));
}

type Boot =
  | { phase: "unreachable" }
  | { phase: "onboarding"; health: Health }
  | {
      phase: "ready";
      health: Health;
      learner: Learner;
      sessions: SessionSummary[];
      progress: Progress;
      session: Session | null;
    };

/**
 * Everything the first screen needs: API health, then the learner from `?learner=` or this
 * browser's cache, their sessions and progress, and the session from `?session=` (or the
 * most recent one).
 */
async function boot(): Promise<Boot> {
  let health: Health;
  try {
    health = await api.health();
  } catch {
    return { phase: "unreachable" };
  }
  const params = new URLSearchParams(window.location.search);
  const learnerId = params.get("learner") ?? learnerCache.get();
  if (!learnerId) return { phase: "onboarding", health };
  try {
    const learner = await api.getLearner(learnerId);
    const [sessions, progress] = await Promise.all([
      api.listSessions(learnerId),
      api.progress(learnerId),
    ]);
    const sessionId = params.get("session") ?? sessions[0]?.session_id;
    const session = sessionId ? await api.getSession(sessionId).catch(() => null) : null;
    return { phase: "ready", health, learner, sessions, progress, session };
  } catch (failure) {
    if (failure instanceof ApiError && failure.status === 404) {
      learnerCache.clear(); // a stale id: start over with onboarding
      return { phase: "onboarding", health };
    }
    return { phase: "unreachable" };
  }
}

/** All client state of the tutor app, and the actions that change it. */
export function useTutor() {
  const { setLanguage, t } = useI18n();
  const [phase, setPhase] = useState<Phase>("loading");
  const [health, setHealth] = useState<Health | null>(null);
  const [learner, setLearner] = useState<Learner | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [hint, setHint] = useState<HintState>({ level: 0, max: 3 });
  const [grade, setGrade] = useState<GradeResult | null>(null);
  const [celebration, setCelebration] = useState(0);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false); // the turn in flight is a submitted answer
  const [rewording, setRewording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nextId = useRef(0);

  const adoptLearner = useCallback(
    (found: Learner) => {
      learnerCache.set(found.learner_id);
      setLearner(found);
      setLanguage(found.preferences.language);
    },
    [setLanguage],
  );

  const refreshLearnerData = useCallback(async (learnerId: string) => {
    const [list, summary] = await Promise.all([
      api.listSessions(learnerId),
      api.progress(learnerId),
    ]);
    setSessions(list);
    setProgress(summary);
    return list;
  }, []);

  const showSession = useCallback((found: Session) => {
    setSession(found);
    setMessages(toMessages(found));
    setHint({ level: found.hint_level, max: found.max_hint_level });
    setGrade(found.last_grade);
    setCelebration(0); // only fresh perfect scores are celebrated
    setRewording(false);
    setError(null);
  }, []);

  const openSession = useCallback(
    async (sessionId: string) => {
      try {
        showSession(await api.getSession(sessionId));
      } catch {
        setError(t("app.error"));
      }
    },
    [showSession, t],
  );

  const applyBoot = useCallback(
    (result: Boot) => {
      if (result.phase !== "unreachable") setHealth(result.health);
      if (result.phase === "ready") {
        adoptLearner(result.learner);
        setSessions(result.sessions);
        setProgress(result.progress);
        if (result.session) showSession(result.session);
      }
      setPhase(result.phase);
    },
    [adoptLearner, showSession],
  );

  useEffect(() => {
    let active = true;
    void boot().then((result) => {
      if (active) applyBoot(result);
    });
    return () => {
      active = false;
    };
  }, [applyBoot]);

  const retry = useCallback(() => {
    setPhase("loading");
    void boot().then(applyBoot);
  }, [applyBoot]);

  const completeOnboarding = useCallback(
    async (profile: LearnerProfile) => {
      const created = await api.createLearner(profile);
      adoptLearner(created);
      await refreshLearnerData(created.learner_id);
      setPhase("ready");
    },
    [adoptLearner, refreshLearnerData],
  );

  const updateProfile = useCallback(
    async (profile: LearnerProfile) => {
      if (!learner) return;
      adoptLearner(await api.updateLearner(learner.learner_id, profile));
      if (session) {
        // Scaffolding may have moved the top of the hint ladder.
        const fresh = await api.getSession(session.session_id);
        setHint({ level: fresh.hint_level, max: fresh.max_hint_level });
      }
    },
    [adoptLearner, learner, session],
  );

  const startSession = useCallback(
    async (spec: Omit<NewSession, "learner_id">) => {
      if (!learner) return;
      try {
        const created = await api.createSession({ ...spec, learner_id: learner.learner_id });
        showSession(created);
        await refreshLearnerData(learner.learner_id);
      } catch {
        setError(t("app.error"));
      }
    },
    [learner, refreshLearnerData, showSession, t],
  );

  const send = useCallback(
    async (content: string, intent: Intent = "auto") => {
      const text = content.trim();
      if (!session || busy || !text) return;
      const studentId = `local-${nextId.current++}`;
      const tutorId = `local-${nextId.current++}`;
      const update = (patch: (message: UIMessage) => Partial<UIMessage>) =>
        setMessages((current) =>
          current.map((m) => (m.id === tutorId ? { ...m, ...patch(m) } : m)),
        );

      setMessages((current) => [
        ...current,
        { id: studentId, role: "student", content: text },
        { id: tutorId, role: "tutor", content: "", streaming: true },
      ]);
      setBusy(true);
      setChecking(intent === "submit");
      setRewording(false);
      setError(null);
      try {
        for await (const event of api.streamMessage(session.session_id, text, intent)) {
          switch (event.type) {
            case "route":
              update(() => ({ route: event.route }));
              break;
            case "hint":
              setHint((h) => ({ level: event.hint_level, max: event.max_hint_level || h.max }));
              break;
            case "token":
              update((m) => ({ content: m.content + event.text }));
              break;
            case "reset":
              update(() => ({ content: "" }));
              setRewording(true);
              break;
            case "grade":
              setGrade(event.grade);
              if (event.grade.percentage === 100) setCelebration((n) => n + 1);
              break;
            case "done":
              update(() => ({ content: event.reply, route: event.route, streaming: false }));
              setHint((h) => ({ ...h, level: event.hint_level }));
              setRewording(false);
              break;
            case "error":
              update(() => ({ streaming: false, failed: true }));
              setError(event.detail);
              break;
          }
        }
      } catch {
        update(() => ({ streaming: false, failed: true }));
        setError(t("app.error"));
      } finally {
        update(() => ({ streaming: false }));
        setBusy(false);
        setChecking(false);
        if (learner) void refreshLearnerData(learner.learner_id).catch(() => undefined);
      }
    },
    [busy, learner, refreshLearnerData, session, t],
  );

  return {
    phase,
    health,
    learner,
    sessions,
    progress,
    session,
    messages,
    hint,
    grade,
    celebration,
    busy,
    checking,
    rewording,
    error,
    retry,
    completeOnboarding,
    updateProfile,
    startSession,
    openSession,
    send,
  };
}

export type TutorState = ReturnType<typeof useTutor>;
