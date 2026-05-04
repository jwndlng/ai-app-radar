FROM python:3.14-slim

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install Python dependencies (cached layer — invalidated only by lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Install Playwright Chromium + system dependencies (cached separately from source)
RUN /app/.venv/bin/playwright install chromium --with-deps

# Copy source, frontend, and default configs (no profile.yaml)
COPY src/ ./src/
COPY static/ ./static/
COPY configs/companies.json configs/settings.yaml configs/profile.example.yaml ./configs/

# Version metadata — passed at build time by CI, defaults to "dev" for local builds
ARG APP_VERSION=dev
LABEL org.opencontainers.image.version=$APP_VERSION
ENV APP_VERSION=$APP_VERSION

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

VOLUME ["/app/configs", "/app/artifacts"]
EXPOSE 8000

CMD ["python", "-m", "main", "serve", "--host", "0.0.0.0"]
