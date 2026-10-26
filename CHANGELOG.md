# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/vulinh1704/ai-tutor-agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vulinh1704/ai-tutor-agent/releases/tag/v0.1.0
