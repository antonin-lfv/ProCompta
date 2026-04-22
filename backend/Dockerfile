FROM debian:bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    poppler-utils \
    curl \
  && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=auto

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Étape 1 : installer les dépendances seules (layer caché tant que lock ne change pas)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Étape 2 : copier le code et installer le projet
COPY . .
RUN uv sync --frozen --no-dev

RUN mkdir -p /app/storage/documents /app/storage/previews

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
