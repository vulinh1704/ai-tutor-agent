import type { Language, LearnerProfile } from "@/lib/types";

export const GRADES = [6, 7, 8, 9, 10, 11, 12] as const;
export const ACCENTS = ["teal", "violet", "orange", "rose", "sky", "green"] as const;
export const AVATARS = ["owl", "cat", "dog", "rabbit", "turtle", "fish"] as const;

export type Accent = (typeof ACCENTS)[number];
export type Avatar = (typeof AVATARS)[number];

/** The level string the tutor sees, in the learner's language ("grade 8", "lớp 8"). */
export function levelFor(grade: number, language: Language): string {
  return language === "vi" ? `lớp ${grade}` : `grade ${grade}`;
}

/** Recover the grade number from a level string, e.g. "lớp 8" -> 8. */
export function gradeOf(level: string): number | null {
  const match = /\d+/.exec(level);
  return match ? Number(match[0]) : null;
}

export function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function defaultProfile(language: Language): LearnerProfile {
  return {
    display_name: "",
    level: levelFor(8, language),
    subjects: [],
    goal: null,
    preferences: { language, tone: "gentle", scaffolding: "standard" },
    appearance: { avatar: "owl", accent: "teal", font_scale: "normal" },
    timezone: browserTimezone(),
  };
}

const LEARNER_KEY = "ai-tutor.learner-id";

/** The learner id remembered in this browser (storage can be unavailable: never throw). */
export const learnerCache = {
  get(): string | null {
    try {
      return window.localStorage.getItem(LEARNER_KEY);
    } catch {
      return null;
    }
  },
  set(learnerId: string): void {
    try {
      window.localStorage.setItem(LEARNER_KEY, learnerId);
    } catch {
      // Private mode or blocked storage: the learner can resume with their link.
    }
  },
  clear(): void {
    try {
      window.localStorage.removeItem(LEARNER_KEY);
    } catch {
      // Nothing to clear.
    }
  },
};

/** A link that reopens this learner (and optionally a session) on another device. */
export function resumeLink(origin: string, learnerId: string, sessionId?: string): string {
  const url = new URL(origin);
  url.searchParams.set("learner", learnerId);
  if (sessionId) url.searchParams.set("session", sessionId);
  return url.toString();
}
