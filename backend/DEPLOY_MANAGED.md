# Managed Backend Deployment

This backend can run on Railway or Render with:

- one web service for FastAPI
- one managed PostgreSQL database
- one managed Redis service

Railway is the simpler option for this project because PostgreSQL, Redis, and
the backend can live in one project and Railway injects service URLs directly.
Render is also fine if you prefer its dashboard and logs, but you will create
separate Web Service, PostgreSQL, and Redis/Key Value resources.

## Backend Build

Use the `backend/` folder as the service root.

Build command:

```bash
uv sync --locked
```

Start command:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port $PORT
```

If the platform uses the Dockerfile, point it at:

```text
backend/dockerfile
```

Health check path:

```text
/health
```

## Database

Create a managed PostgreSQL database and set:

```text
DATABASE_URL=<provider-postgres-url>
```

Provider URLs such as `postgres://...` and `postgresql://...` are normalized by
the app for SQLAlchemy async connections.

After the first deploy, run:

```bash
uv run alembic upgrade head
```

On Railway, run it from the backend service shell. On Render, use a shell or a
one-off job.

## Redis

Create a managed Redis service and set:

```text
REDIS_URL=<provider-redis-url>
```

The FastAPI app pings Redis at startup, so the backend will not boot unless
Redis is reachable.

## Required Environment

Start from `.env.production.example` and fill in secrets in the platform
dashboard. At minimum, production needs:

```text
APP_NAME
APP_URL
FRONTEND_URL
DATABASE_URL
REDIS_URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
JWT_SECRET
REFRESH_TOKEN_EXPIRY_DAYS
GROQ_API_KEY
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM_EMAIL
ADMIN_EMAIL
```

## Google OAuth

In Google Cloud Console, add this authorized redirect URI:

```text
https://your-backend-domain.example/api/v1/auth/google/callback
```

Then set the same value as `GOOGLE_REDIRECT_URI`.
