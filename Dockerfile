# syntax=docker/dockerfile:1

# ---------------------------------------------------------------- build stage
FROM python:3.15-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first, so code changes don't invalidate this layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --extra sqlite

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --extra sqlite

# -------------------------------------------------------------- runtime stage
FROM python:3.15-slim

RUN useradd --create-home --uid 10001 tutor \
    && mkdir -p /data \
    && chown tutor:tutor /data

COPY --from=builder --chown=tutor:tutor /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    CHECKPOINTER=sqlite \
    SQLITE_PATH=/data/checkpoints.sqlite

USER tutor
WORKDIR /app
EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

CMD ["ai-tutor", "serve", "--host", "0.0.0.0", "--port", "8000"]
