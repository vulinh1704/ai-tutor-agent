// Shapes returned by the ai-tutor-agent HTTP API (see src/ai_tutor_agent/api/models.py).

export type Route = "tutor" | "grader" | "clarify";
export type Language = "en" | "vi";
export type Tone = "gentle" | "direct";
export type Scaffolding = "less" | "standard" | "more";
export type FontScale = "normal" | "large" | "x-large";
export type TutorMode = "homework" | "explain";
export type Intent = "auto" | "submit";

export interface TutorPreferences {
  language: Language;
  tone: Tone;
  scaffolding: Scaffolding;
}

export interface Appearance {
  avatar: string;
  accent: string;
  font_scale: FontScale;
}

export interface LearnerProfile {
  display_name: string;
  level: string;
  subjects: string[];
  goal: string | null;
  preferences: TutorPreferences;
  appearance: Appearance;
  timezone: string;
}

export interface Learner extends LearnerProfile {
  learner_id: string;
  created_at: string;
  updated_at: string;
}

export interface Criterion {
  id: string;
  description: string;
  max_points: number;
}

export interface Rubric {
  criteria: Criterion[];
}

export interface CriterionScore {
  criterion_id: string;
  points: number;
  max_points: number;
  feedback: string;
}

export interface GradeResult {
  score: number;
  max_score: number;
  percentage: number;
  criteria: CriterionScore[];
  next_step_hint: string;
}

export interface Assignment {
  question: string;
  rubric: Rubric | null;
  has_reference_answer: boolean;
  skills: string[];
}

export interface ChatMessage {
  role: "student" | "tutor";
  content: string;
}

export interface Session {
  session_id: string;
  subject: string;
  level: string;
  mode: TutorMode;
  learner_id: string | null;
  assignment: Assignment | null;
  hint_level: number;
  max_hint_level: number;
  created_at: string | null;
  messages: ChatMessage[];
  last_grade: GradeResult | null;
}

export interface NewSession {
  subject: string;
  level: string;
  mode: TutorMode;
  learner_id: string;
  assignment?: {
    question: string;
    rubric?: Rubric;
    reference_answer?: string;
    skills?: string[];
  } | null;
}

export interface SessionSummary {
  session_id: string;
  subject: string;
  mode: TutorMode;
  title: string;
  created_at: string;
  last_active_at: string | null;
  turns: number;
  graded_attempts: number;
  best_percentage: number | null;
  last_percentage: number | null;
}

export interface SubjectProgress {
  subject: string;
  sessions: number;
  graded_attempts: number;
  average_score: number | null;
}

export interface Progress {
  sessions: number;
  graded_attempts: number;
  average_score: number | null;
  current_streak: number;
  best_streak: number;
  active_today: boolean;
  last_active_on: string | null;
  subjects: SubjectProgress[];
}

export interface Health {
  status: "ok";
  version: string;
  llm_provider: string;
  llm_model: string;
  checkpointer: string;
}

/** Server-sent events of POST /sessions/{id}/messages/stream. */
export type TurnEvent =
  | { type: "route"; route: Route; reason: string; new_problem: boolean }
  | { type: "hint"; hint_level: number; max_hint_level: number }
  | { type: "token"; text: string }
  | { type: "reset"; reason: "answer_leak" }
  | { type: "grade"; grade: GradeResult }
  | {
      type: "done";
      session_id: string;
      route: Route;
      reply: string;
      hint_level: number;
      grade: GradeResult | null;
    }
  | { type: "error"; status: number; detail: string };
