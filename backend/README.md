# ORCA - Stage 1 - Phase 1

This is the backend foundation for ORCA (Marine EcOsystem Reasoning with Collaborative Agents). Phase 1 establishes the core infrastructure, database architecture, caching, background processing, and LLM provider interfaces.

## Requirements

- Python 3.x
- PostgreSQL
- Valkey/Redis-compatible server

## Database Setup

Create the development database:

```bash
createdb orca
# Or via psql:
# psql -c "CREATE DATABASE orca;"
```

## Environment Setup

Create an environment configuration file:

```bash
cp .env.example .env
```
Update `.env` with appropriate credentials. The application requires PostgreSQL and Redis, and supports optional API keys for Groq, Gemini, and OpenRouter.

## Migration

Initialize the database schema using Alembic migrations:

```bash
alembic upgrade head
```

## Seed

Seed the foundational metadata (workspaces and data sources):

```bash
python seed.py
```

## Run Backend

Start the FastAPI application via Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Celery

Start the Celery worker for background processing:

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## Verify Valkey / Redis

Ensure Valkey or Redis is running:

```bash
redis-cli ping
```
Expected output:
```text
PONG
```

## Verify API

The following standard endpoints are available:

- `GET /health` : Liveness check
- `GET /ready` : Readiness check verifying PostgreSQL and Redis connections
- `GET /api/v1/llm/providers` : Lists configuration status of LLM providers

## LLM Configuration

The system uses a fallback routing model for LLM requests:

1. **Groq** = primary
2. **Gemini** = fallback #1
3. **OpenRouter** = fallback #2

You can configure models and API keys in `.env`.

## Important Credential Distinction

- **Groq** → Requires an API key (GROQ_API_KEY)
- **Gemini** → Requires an API key (GEMINI_API_KEY)
- **OpenRouter** → Requires an API key (OPENROUTER_API_KEY)
- **NASA Earthdata** → dataset/service-dependent authentication (not required in Phase 1)
- **MOSDAC** → account authentication where required (not required in Phase 1)
- **Open-Meteo** → no API key for the selected public service
- **OpenStreetMap** → no API key for normal public tile usage
