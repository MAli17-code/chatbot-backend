FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Install dependencies first (better layer caching)
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-install-project

# Then add the source and install the project itself
COPY src ./src
RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "chatbot_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]