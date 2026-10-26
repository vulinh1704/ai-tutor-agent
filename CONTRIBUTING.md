# Contributing

Thanks for your interest in improving `ai-tutor-agent`! Bug reports, ideas and pull requests
are all welcome.

## Development setup

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/). For the web UI, Node.js 22.12+.

```bash
git clone https://github.com/vulinh1704/ai-tutor-agent.git
cd ai-tutor-agent
make install        # uv sync --all-extras && uv run pre-commit install
make check          # ruff, mypy and pytest: the same checks CI runs
make web-install    # npm ci in web/
make web-check      # web lint, typecheck, tests and production build
```

No API key is needed for development: set `LLM_PROVIDER=fake` (the default in
`.env.example`) to run the API, the MCP server, the web UI and the demo against the
deterministic offline model.

## Workflow

1. Open an issue first for anything non-trivial, so we can agree on the approach.
2. Create a branch from `main` (`feat/streaming-replies`, `fix/grading-retry`, ...).
3. Keep changes focused, with tests. `make check` (and `make web-check` for `web/`) must pass.
4. Write [Conventional Commits](https://www.conventionalcommits.org/) messages:
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:`, `chore:` (use the `web` scope for
   the web UI, e.g. `feat(web): ...`).
5. Open a pull request and fill in the template. Update `CHANGELOG.md` under
   *Unreleased* when behaviour or configuration changes.

## Guidelines

- **Tests never hit the network.** Use `FakeChatModel`: queue exact outputs with
  `replies=[...]` / `structured=[...]` (or an exception to simulate a failure) and assert on
  the prompts it recorded in `fake.calls`. The tutor node streams, so its calls have the kind
  `"stream"`.
- **Streaming keeps the guard.** Any text that reaches the student must pass the answer-leak
  guard first: emit tutor text through `StreamGuard`, never straight from the model.
- **Types.** `src/` is checked with `mypy --strict`, `web/` with `tsc` in strict mode. Avoid
  `Any` and `type: ignore` unless a third-party API forces it, and leave a comment when it does.
- **Style.** Ruff handles Python linting, import order and formatting (line length 100); ESLint
  with `eslint-config-next` checks the web app.
- **Prompts.** Wrap untrusted input (questions, rubrics, student answers, learner names and
  goals) in XML-style tags via `prompts.tag()`, and keep LLM-facing schemas simple. Put
  validation in code.
- **Learner-facing text.** Write for students aged 12-18: encouraging, never condescending.
  Every UI string needs English and Vietnamese (`web/src/lib/i18n.ts`; TypeScript checks that
  none is missing), and canned tutor replies live in `src/ai_tutor_agent/i18n.py`.
- **Accessibility and motion.** Keep controls keyboard-reachable with visible focus, keep
  contrast high, and make animations respect `prefers-reduced-motion`.
- **Security and privacy.** Never commit API keys, `.env` files or real student data. Use
  placeholders in docs and synthetic examples in tests.

## Common extension points

- **New provider:** add a branch to `llm/factory.py` that wraps a LangChain chat model in
  `LangChainChatModel`, plus tests in `tests/test_llm_factory.py` that build it with sockets
  disabled.
- **New node:** implement it in `agent/nodes.py`, wire it in `agent/graph.py`, extend `Route`
  and the router prompt, emit its events with `agent.events.emit`, and add graph tests that
  drive it through `TutorService`.
- **New checkpointer or store:** extend `agent/checkpointer.py`; sessions and learners need no
  other changes.
- **New MCP tool:** add it in `mcp_server.py` on top of `TutorService`, and test it in process
  with the SDK's `Client` in `tests/test_mcp.py`.
- **New reply language:** add it to `Language` in `schemas.py`, to `i18n.py` and
  `prompts.LANGUAGE_RULES`, to the fake model's texts, and to the web UI's `i18n.ts`.

## Reporting security issues

Please don't open a public issue for security problems. Contact the maintainer through the
links in the README instead.
