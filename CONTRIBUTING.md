# Contributing

Thanks for your interest in improving `ai-tutor-agent`! Bug reports, ideas and pull requests
are all welcome.

## Development setup

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/vulinh1704/ai-tutor-agent.git
cd ai-tutor-agent
make install        # uv sync --all-extras && uv run pre-commit install
make check          # ruff, mypy and pytest: the same checks CI runs
```

No API key is needed for development: set `LLM_PROVIDER=fake` (the default in
`.env.example`) to run the API and the demo against the deterministic offline model.

## Workflow

1. Open an issue first for anything non-trivial, so we can agree on the approach.
2. Create a branch from `main` (`feat/streaming-replies`, `fix/grading-retry`, ...).
3. Keep changes focused, with tests. `make check` must pass.
4. Write [Conventional Commits](https://www.conventionalcommits.org/) messages:
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:`, `chore:`.
5. Open a pull request and fill in the template. Update `CHANGELOG.md` under
   *Unreleased* when behaviour or configuration changes.

## Guidelines

- **Tests never hit the network.** Use `FakeChatModel`: queue exact outputs with
  `replies=[...]` / `structured=[...]` (or an exception to simulate a failure) and assert on
  the prompts it recorded in `fake.calls`.
- **Types.** `src/` is checked with `mypy --strict`. Avoid `Any` and `type: ignore` unless a
  third-party API forces it, and leave a comment when it does.
- **Style.** Ruff handles linting, import order and formatting (line length 100).
- **Prompts.** Wrap untrusted input (questions, rubrics, student answers) in XML-style tags via
  `prompts.tag()`, and keep LLM-facing schemas simple. Put validation in code.
- **Security and privacy.** Never commit API keys, `.env` files or real student data. Use
  placeholders in docs and synthetic examples in tests.

## Common extension points

- **New provider:** add a branch to `llm/factory.py` that wraps a LangChain chat model in
  `LangChainChatModel`, plus tests in `tests/test_llm_factory.py` that build it with sockets
  disabled.
- **New node:** implement it in `agent/nodes.py`, wire it in `agent/graph.py`, extend `Route`
  and the router prompt, and add graph tests that drive it through `TutorService`.
- **New checkpointer:** extend `agent/checkpointer.py`; sessions need no other changes.

## Reporting security issues

Please don't open a public issue for security problems. Contact the maintainer through the
links in the README instead.
