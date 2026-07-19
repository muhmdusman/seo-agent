# Search Console Agent — Backend

Backend service for **Search Console Agent**, a FastAPI application that
authenticates users with Google OAuth 2.0 and requests read access to the
[Google Search Console API](https://developers.google.com/webmaster-tools)
(`webmasters.readonly` scope) on their behalf.

## Tech Stack

- **Python** 3.11+
- **FastAPI** — web framework
- **SQLAlchemy 2.0** (async) — ORM
- **PostgreSQL 17** — database
- **Alembic** — database migrations
- **google-auth** / **httpx** — Google OAuth 2.0 code exchange & ID token verification
- **Pydantic / pydantic-settings** — schemas & config
- **uv** — dependency management

## Project Structure

```
backend/
├── main.py                  # FastAPI app instance (entry point)
├── api/
│   ├── main.py               # /api/v1 router, mounts feature routers
│   └── routes/
│       └── auth.py           # /auth/google, /auth/google/callback
├── core/
│   ├── config.py             # Settings loaded from environment/.env
│   └── enums.py              # OAuthProvider enum
├── db/
│   ├── dbconfig.py           # Async SQLAlchemy engine/session
│   └── docker-compose.yaml   # Postgres + Adminer for local dev
├── models/
│   ├── base.py                # Declarative Base + TimestampMixin
│   ├── user.py                 # User model
│   ├── oauth_account.py        # OAuthAccount model
│   └── session.py              # Session model
├── schemas/
│   ├── auth.py                 # GoogleRegisterData
│   ├── google_oauth.py         # GoogleTokenResponse
│   └── google_user.py          # GoogleUserInfo
├── services/
│   ├── auth_service.py          # Login / registration orchestration
│   ├── google_oauth.py          # Google OAuth 2.0 HTTP calls
│   ├── oauth_service.py         # OAuthAccount persistence
│   └── user_service.py          # User persistence
├── alembic/                    # Migration environment & versions
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose (for the local Postgres instance)
- A Google Cloud OAuth 2.0 Client ID (Web application) with the
  `webmasters.readonly` scope enabled

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Start Postgres

```bash
docker compose -f db/docker-compose.yaml up -d
```

This starts:

| Service  | Purpose                  | Port |
|----------|--------------------------|------|
| postgres | PostgreSQL 17 database   | 5433 |
| adminer  | Web UI for the database  | 8081 |

Default credentials: `postgres` / `postgres`, database `app_db`.

### 3. Configure environment variables

Create a `.env` file in `backend/` (values are read via
`core/config.py`):

```env
APP_NAME=Search Console Agent
DEBUG=true
APP_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Postgres connection string used by SQLAlchemy (async driver)
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/app_db

# Google OAuth 2.0 credentials
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# JWT signing (issued after successful login)
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_NAME` | yes | — | Displayed as the FastAPI app title |
| `DEBUG` | no | `false` | Enables FastAPI debug mode + SQL echo |
| `APP_URL` | yes | — | Public base URL of this backend |
| `FRONTEND_URL` | yes | — | Base URL of the frontend app; used for CORS and post-login redirects |
| `DATABASE_URL` | yes | — | Async SQLAlchemy connection string |
| `GOOGLE_CLIENT_ID` | yes | — | OAuth client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | yes | — | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | yes | — | Must match the redirect URI configured in Google Cloud Console |
| `JWT_SECRET` | yes | — | Secret used to sign issued JWTs |
| `JWT_ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `60` | Access token lifetime |

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

### 5. Run the application

```bash
uv run fastapi dev main.py
```

or with uvicorn directly:

```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` (interactive docs at
`/docs`).

## API Reference

All routes are mounted under the `/api/v1` prefix (see `api/main.py`).

### Authentication — `/api/v1/auth`

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/google` | Redirects the user to Google's OAuth 2.0 consent screen. |
| `GET` | `/auth/google/callback` | Handles the OAuth callback: exchanges the `code` for tokens, verifies the ID token, and logs in or registers the user. |

**OAuth flow:**

1. Client hits `GET /api/v1/auth/google` → 302 redirect to Google's
   consent screen, requesting `openid`, `email`, and
   `https://www.googleapis.com/auth/webmasters.readonly` scopes with
   `access_type=offline` (so a refresh token is issued).
2. Google redirects back to `GOOGLE_REDIRECT_URI` with a `code` query
   parameter.
3. `GET /api/v1/auth/google/callback?code=...` exchanges the code for
   access/refresh tokens, verifies the Google ID token, then:
   - If a matching `OAuthAccount` already exists, its tokens are updated
     and the linked `User` is returned.
   - Otherwise, a new `User` and `OAuthAccount` are created
     (`AuthService.register_with_google`).
4. The backend redirects the browser to
   `${FRONTEND_URL}/callback?status=success&email=...` (or
   `status=error` on failure) so the frontend can complete the flow.

> **Note:** `JWT_SECRET` / `ACCESS_TOKEN_EXPIRE_MINUTES` and the
> `sessions` table are already configured but issuing/validating a real
> JWT session is not yet wired into `AuthService` — the callback
> currently redirects with the user's email in the query string only.
> This is fine to get the frontend flow working end-to-end, but should
> be replaced with a proper session/JWT cookie before shipping.

## Data Model

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `username` | String(50) | Unique |
| `email` | String(255) | Unique |
| `created_at` / `updated_at` | DateTime | Auto-managed |

### `oauth_accounts`

Links a `User` to a third-party identity provider.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → `users.id`, cascade delete |
| `provider` | Enum (`OAuthProvider`) | Currently only `google` |
| `provider_user_id` | String(255) | Unique; the Google account ID |
| `access_token` | String | Google OAuth access token |
| `refresh_token` | String | Google OAuth refresh token |
| `expires_at` | DateTime | Access token expiry |

### `sessions`

Tracks issued refresh tokens for a `User`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → `users.id`, cascade delete |
| `refresh_token_hash` | String | Hashed refresh token |
| `expires_at` | DateTime | Session expiry |
| `revoked` | Boolean | Defaults to `false` |

## Database Migrations (Alembic)

Migrations live under `alembic/versions/` and connect using the
`DATABASE_URL` from `core/config.py` (see `alembic/env.py`).

```bash
# Create a new migration after changing a model
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Roll back one revision
uv run alembic downgrade -1
```

## Development Notes

- Database sessions are provided via the `get_db` async generator in
  `db/dbconfig.py` and injected with FastAPI's `Depends`.
- Service layer (`services/`) separates business logic from routes:
  - `GoogleOAuthService` — talks to Google's OAuth endpoints.
  - `UserService` / `OAuthService` — persistence for users and linked
    OAuth accounts.
  - `AuthService` — orchestrates login/registration using the services
    above.
