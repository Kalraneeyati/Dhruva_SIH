FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Dependency layer first so code edits do not reinstall the world.
COPY pyproject.toml ./
COPY dhruva/__init__.py ./dhruva/
RUN uv pip install --system --no-cache -e ".[dev]"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "dhruva.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
