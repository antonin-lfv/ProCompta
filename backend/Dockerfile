FROM debian:bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    poppler-utils \
  && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update && apt-get install -y --no-install-recommends postgresql-client-16 \
  && rm -rf /var/lib/apt/lists/*

# Tailwind CSS standalone CLI (pas de Node.js nécessaire)
RUN curl -sL https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 \
    -o /usr/local/bin/tailwindcss \
  && chmod +x /usr/local/bin/tailwindcss

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

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
