# tech-pulse-engine

`tech-pulse-engine` is a Python automation platform for collecting Africa-relevant tech opportunities, qualifying and ranking them, storing them in a structured database, and producing WhatsApp-ready drafts plus a daily markdown digest.

## Recommended Runtime

Docker is now the default way to run the system.

Why Docker is the primary path:

- the Python runtime is pinned and reproducible
- dependencies are isolated without relying on a local `.venv`
- PostgreSQL, scheduler, dashboard, and pipeline tooling run as one stack
- onboarding and deployment use the same operational model

A local virtual environment is still fine for quick development work, but it is now optional rather than the main workflow.

## Enterprise Architecture

The project uses a service-oriented architecture instead of a single ingestion script.

Core layers:

- collection adapters for RSS and strategy-driven HTML sources
- parsing and qualification for categorization, date extraction, and opportunity filtering
- ranking and deduplication for scoring and canonicalization
- persistence for opportunities plus operational telemetry
- orchestration services for daily execution and digest generation
- operations dashboard for monitoring pipeline health and publishing readiness

Operational telemetry is stored in two additional tables:

- `pipeline_runs` tracks each run end to end
- `source_runs` tracks per-source status, throughput, timing, and failures

## Stack

- Python 3.11+ locally, with Docker defaulting to Python `${PYTHON_VERSION:-3.11}`
- SQLAlchemy with PostgreSQL or SQLite fallback
- `feedparser` for RSS ingestion
- `requests` and `beautifulsoup4` for HTML and structured page extraction
- APScheduler for daily scheduling
- `python-dotenv` for configuration
- FastAPI + Jinja2 + Uvicorn for the monitoring dashboard
- Docker + Docker Compose for deployment and operations

## Project Layout

```text
tech-pulse-engine/
  app/
    collectors/
    config/
    dashboard/
    db/
    formatters/
    notify/
    parsers/
    rankers/
    services/
    main.py
  docker/
    entrypoint.sh
  Dockerfile
  docker-compose.yml
  .dockerignore
  .env.example
  README.md
  requirements.txt
```

## Docker Quick Start

1. Create your environment file.

```bash
cp .env.example .env
```

2. Build and start the main stack.

```bash
docker compose up --build -d postgres dashboard scheduler
```

3. Open the operations dashboard.

```text
http://127.0.0.1:8080/dashboard
```

4. Run an on-demand collection pass.

```bash
docker compose run --rm app-runner
```

5. Stop the stack.

```bash
docker compose down
```

If you also want to remove PostgreSQL state:

```bash
docker compose down -v
```

## Compose Services

The Compose stack now includes:

- `postgres`: primary operational database
- `dashboard`: FastAPI monitoring console with `/healthz`
- `scheduler`: long-running APScheduler service for daily automation
- `app-runner`: one-shot manual pipeline execution service

The image entrypoint initializes the database schema on startup and retries until Postgres is reachable.

## CLI Commands

These commands still work inside or outside Docker:

```bash
python -m app.main init-db
python -m app.main run-daily
python -m app.main schedule-daily
python -m app.main serve-dashboard
```

Inside Docker, the equivalent commands are exposed through Compose service commands.

## What `run-daily` Does

`python -m app.main run-daily` performs the full managed pipeline:

- loads `app/config/sources.yaml`
- records a `pipeline_runs` entry
- records a `source_runs` entry for each source
- collects RSS and HTML opportunities
- classifies and filters for actionable Africa-relevant programs
- deduplicates by canonical link and title similarity
- ranks by urgency, relevance, and keyword boosts
- generates WhatsApp short and detailed drafts
- stores new opportunities in the database
- writes `daily_digest.md` or the configured digest path

## Dashboard

Start the operations console locally with:

```bash
python -m app.main serve-dashboard
```

Or through Docker with:

```bash
docker compose up -d dashboard
```

The dashboard exposes:

- latest pipeline execution status
- recent run throughput trend
- per-source health and rolling reliability
- source alerts for failing or degraded inputs
- category and workflow distribution
- recent opportunities waiting for approval or posting
- JSON summary API at `/api/dashboard/summary`

## Source Coverage

The source registry combines:

- Africa tech and startup media feeds
- opportunity aggregator feeds
- training and certification portals
- event platforms and program landing pages

Current notable sources include:

- TechCabal
- Disrupt Africa
- Ventureburn
- Opportunities for Africans
- Opportunity Desk
- AfriLabs
- Google Skills
- Linux Foundation Training
- Cisco Networking Academy
- Microsoft Learn Events
- ISC2 Programs

HTML collection is strategy-driven rather than generic-first. Current adapter strategies include:

- embedded JSON extraction
- sitemap-driven detail discovery
- curated metadata extraction
- targeted certification and event scraping

## Configuration

Important environment variables:

- `DATABASE_URL`
- `REQUEST_TIMEOUT`
- `USER_AGENT`
- `LOG_LEVEL`
- `DIGEST_PATH`
- `DAILY_RUN_HOUR`
- `DAILY_RUN_MINUTE`
- `MIN_AFRICA_SCORE`
- `DASHBOARD_PORT`
- `DASHBOARD_TITLE`
- `DASHBOARD_REFRESH_SECONDS`
- `INIT_DB_ATTEMPTS`
- `INIT_DB_DELAY_SECONDS`

Use `.env.example` as the starting point for Docker deployments.

## Notes

- Docker is the recommended path for reproducible execution.
- Local `.venv` usage is still supported for development, but it is optional.
- Per-source logs are written to `logs/`.
- Docker writes persistent digest and runtime artifacts to `./data`.
- Linux Foundation and Cisco still rely on sitemap-driven discovery because their catalog pages are JavaScript shells.
- The data model is telemetry-ready, but schema changes still use `Base.metadata.create_all()` rather than a formal migration tool.
- For larger deployments, the next step is Alembic migrations plus dashboard authentication and a dedicated worker queue.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```
