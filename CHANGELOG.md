# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-26

### Added

- Streaming: `POST /sessions/{id}/messages/stream` sends a chat turn as server-sent events
  (`route`, `hint`, `token`, `reset`, `grade`, `done`, `error`), and
  `TutorService.stream_message()` yields the same typed events in Python. Streamed turns run in
  their own task, so a dropped connection never leaves a half-saved turn.
- Guarded streaming: `StreamGuard` releases streamed text only after the answer-leak guard has
  checked it, holding back the start of a leaking phrase; a rejected draft sends `reset` and is
  regenerated.
- MCP server mode: `ai-tutor mcp` (stdio or `--transport streamable-http`) exposes the tools
  `create_learner`, `start_session`, `ask_tutor`, `submit_answer`, `grade_answer` and
  `get_progress`, plus the resource `tutor://sessions/{id}/transcript`, with the official MCP
  Python SDK (new `mcp` extra). Setup for Claude Desktop, Claude Code and Cursor in the README.
- Learner profiles: `POST /learners`, `GET`/`PUT /learners/{id}` with display name, level,
  subjects, goal, reply language (English or Vietnamese), tone (gentle or direct), scaffolding
  (less, standard or more), appearance and time zone. Sessions accept a `learner_id`.
- Personalised prompts: a `<learner>` block and language, tone and scaffolding rules in the
  tutor, router and grader prompts; scaffolding shifts the hint ladder; canned replies and
  grade summaries are localised; the leak guard recognises Vietnamese giveaways.
- Progress: `GET /learners/{id}/progress` (sessions practised, graded attempts, average rubric
  score, current and best day streaks in the learner's time zone, per-subject averages) and
  `GET /learners/{id}/sessions`. Graded attempts are stored with per-criterion scores and the
  assignment's new optional `skills` tags. Profiles and progress live in a LangGraph store
  (memory, or SQLite with `CHECKPOINTER=sqlite`).
- `intent: "submit"` on chat messages sends an answer straight to the grader.
- Session responses include `learner_id`, `max_hint_level` and `last_grade`.
- Web UI (`web/`): Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui and Animate UI.
  Onboarding, streaming chat, hint-ladder stepper, "grade my answer" panel with per-criterion
  scores, progress panel, session sidebar, light and dark themes, English and Vietnamese,
  responsive and reduced-motion aware. Vitest tests, a Dockerfile and a Compose service.
- The offline demo shows a personalised, streamed session; the fake model streams word by word
  (`FAKE_STREAM_DELAY_MS`) and follows language, tone and scaffolding.
- `CORS_ORIGINS` setting, CI job for the web app (lint, typecheck, tests, build), web image
  build and streaming smoke test in the Docker job, Dependabot for npm.
- `THIRD_PARTY_NOTICES.md` (Animate UI is used under MIT + Commons Clause as an npm dependency).

### Changed

- `ChatModel` protocol gains `stream()`; custom implementations must add it. The tutor node now
  streams drafts from the model (identical replies when not streaming).
- The API and the MCP server share `open_service()`, which opens the checkpointer and the
  store together.
- The Docker image installs the `mcp` extra; `tzdata` is a new dependency.

### Fixed

- `run_demo()` resolved `sys.stdout` at import time, so redirected output was ignored.

## [0.1.0] - 2026-10-26

### Added

- LangGraph tutoring graph: a router node sends each message to the tutor, the grader or a
  clarifying question, with guardrails applied in code.
- Socratic tutor with a configurable hint ladder (`MAX_HINT_LEVEL`) in homework mode and full
  explanations in explain mode.
- Answer-leak guard that regenerates or replaces replies revealing the final answer, also
  applied to the grader's next-step hint.
- Rubric-based grading with structured output, rubric validation, code-computed totals and one
  corrective retry.
- Session memory as LangGraph threads, with in-memory and SQLite checkpointers.
- FastAPI endpoints: `GET /health`, `POST /sessions`, `GET /sessions/{id}`,
  `POST /sessions/{id}/messages` and `POST /grade`.
- LLM provider abstraction with OpenAI (default), Anthropic Claude and a deterministic offline
  fake model.
- `ai-tutor` CLI with `serve`, `demo` (offline) and `graph` (Mermaid) commands.
- Docker image, Docker Compose setup, GitHub Actions CI (Python 3.11 to 3.14), pre-commit hooks
  and Dependabot configuration.

[Unreleased]: https://github.com/vulinh1704/ai-tutor-agent/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/vulinh1704/ai-tutor-agent/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/vulinh1704/ai-tutor-agent/releases/tag/v0.1.0
