<div align="center">

# Search Console Agent

**An automated SEO reporting system that generates daily insights from Google Search Console data using AI-powered analysis.**

Deployed on AWS infrastructure with automated daily reports delivered via email.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![AWS](https://img.shields.io/badge/AWS-Deployed-orange.svg?style=for-the-badge&logo=amazonaws)](https://main.d3vozze6u0rukp.amplifyapp.com/)

</div>

## 🚀 Live Demo

- **Frontend:** https://main.d3vozze6u0rukp.amplifyapp.com/
- **Backend API:** http://search-console-prod.eba-auaxqesy.us-east-1.elasticbeanstalk.com
- **Repository:** https://github.com/muhmdusman/seo-agent

## ☁️ AWS Architecture

This application is fully deployed on AWS using:

- **AWS Amplify** - Frontend hosting with CI/CD
- **AWS Elastic Beanstalk** - Backend API (FastAPI)
- **AWS RDS PostgreSQL** - Database
- **AWS Lambda** - Automated report generation
- **AWS EventBridge** - Daily scheduling (8 AM UTC)
- **AWS CloudWatch** - Logging and monitoring

## Tech Stack

<div align="center">

![Python](https://img.shields.io/badge/Python%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy%202-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL%2017-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS%204-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Radix UI](https://img.shields.io/badge/Radix%20UI-161618?style=for-the-badge&logo=radixui&logoColor=white)

![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Mistral AI](https://img.shields.io/badge/Mistral%20AI-FA520F?style=for-the-badge&logo=mistralai&logoColor=white)
![Google Search Console](https://img.shields.io/badge/Search%20Console-458CF5?style=for-the-badge&logo=googlesearchconsole&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)

</div>

## 🏗️ How It Works

The system automates SEO monitoring by:

1. **Authentication** - Users sign in with Google OAuth to access Search Console data
2. **Site Selection** - Choose from verified Search Console properties
3. **Data Collection** - Fetch 30-day performance metrics automatically
4. **AI Analysis** - Generate insights using Mistral AI
5. **Report Delivery** - Email reports daily at 8 AM UTC via AWS Lambda
6. **Continuous Monitoring** - AWS EventBridge ensures reports run every day

### Architecture Diagram

```
User Browser
    ↓
AWS Amplify (Frontend)
    ↓
AWS Elastic Beanstalk (Backend API)
    ↓
AWS RDS PostgreSQL (Database)

AWS EventBridge (Daily 8 AM UTC)
    ↓
AWS Lambda (Report Generation)
    ↓
Google Search Console API → Mistral AI → SMTP Email
```

## ✨ Features

- 🔐 **Google OAuth 2.0 authentication** with `webmasters.readonly` scope
- 📊 **Google Search Console integration** for performance data
- 🤖 **AI-powered insights** using Mistral API
- 📧 **Automated email delivery** via SMTP
- ⏰ **Daily automated reports** via AWS Lambda + EventBridge
- 🌐 **Multi-site support** - manage multiple Search Console properties
- 📱 **Responsive web interface** built with Next.js
- ☁️ **Fully cloud-deployed** on AWS infrastructure

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| [Python](https://www.python.org/) | 3.11+ | Pinned in `backend/.python-version` |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Dependency and venv management |
| [Node.js](https://nodejs.org/) | 20+ | Next.js 16 |
| [Docker](https://docs.docker.com/get-docker/) + Compose | latest | Local PostgreSQL |
| Google Cloud project | — | OAuth client + Search Console API |
| [Mistral API key](https://console.mistral.ai/) | — | Generates the recommendations |

## Google Cloud setup

Do this first. Most setup failures happen here, not in the code.

1. Create or select a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Google Search Console API** under *APIs & Services → Library*.
3. Under *Google Auth Platform → Clients*, create an **OAuth client ID** of type *Web application* and add this authorized redirect URI:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
4. Under *Google Auth Platform → Audience*, set **User type** to *External* and register the scopes `openid`, `email`, and `.../auth/webmasters.readonly`.
5. Add your own Google account under **Test users**.

> [!IMPORTANT]
> `webmasters.readonly` is a sensitive scope. While the app sits in **Testing**, only accounts on the test-user list can complete the flow, and everyone else gets `Error 403: access_denied` before the consent screen appears. Expect an "unverified app" warning on first sign-in; continue via *Advanced*.

## Configuration

Create a `.env` in the repository root:

```env
APP_NAME="Search Console Agent"
DEBUG=true
APP_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5433/app_db"

GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"

JWT_SECRET="generate-a-long-random-string"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRY_DAYS=7

MISTRAL_API_KEY="your-mistral-api-key"
```

| Variable | Purpose |
|---|---|
| `APP_NAME` | FastAPI application title shown in the OpenAPI docs |
| `DEBUG` | FastAPI debug mode and SQLAlchemy statement echo |
| `APP_URL` | Declared in settings; currently unused by request handling |
| `FRONTEND_URL` | Post-OAuth redirect target **and** the only allowed CORS origin |
| `DATABASE_URL` | Async SQLAlchemy connection string; also used by Alembic |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Identify and authenticate the *application* to Google. One pair serves every user; per-user tokens live in the database |
| `GOOGLE_REDIRECT_URI` | Must match the Google Cloud registration byte for byte |
| `JWT_SECRET` / `JWT_ALGORITHM` | Sign and verify this app's own access and refresh cookies |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRY_DAYS` | Cookie and session lifetimes |
| `MISTRAL_API_KEY` | Authenticates `ChatMistralAI` for the analysis call |

The frontend reads one browser-visible value from `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Setup and run

### Backend

```bash
# Point the backend at the root .env (config.py resolves ./.env against the cwd)
cd backend && ln -sfn ../.env .env

# Install Python dependencies into backend/.venv
uv sync

# Start PostgreSQL 17 + Adminer
docker compose -f db/docker-compose.yaml up -d

# Apply migrations
uv run alembic upgrade head

# Run the API with hot reload
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

API at `http://localhost:8000`, interactive docs at `/docs`, Adminer at `http://localhost:8081`.

> [!NOTE]
> The symlink in step one matters. `backend/core/config.py` sets `env_file=".env"`, which resolves relative to the working directory, so running uvicorn from `backend/` will not find a root-level `.env` without it.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App at `http://localhost:3000`. Keep it on port 3000, since `FRONTEND_URL` is the only origin the backend's CORS config allows.

### Verify

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/openapi.json    # 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/auth/me  # 401 without cookies
```

## API reference

All routes are mounted under `/api/v1`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/auth/google` | — | 302 redirect to Google's consent screen |
| `GET` | `/auth/google/callback` | — | Exchanges `code`, persists user/account/credential/session, sets cookies, redirects to the frontend |
| `GET` | `/auth/me` | Cookie | Returns the authenticated local user ID |
| `POST` | `/auth/logout` | — | Clears both auth cookies |
| `GET` | `/search-console/sites` | Cookie | Lists Search Console properties for the linked Google account |
| `GET` | `/agent/weekly` | — | SSE stream of analysis progress and the final recommendation |

The weekly stream emits `data: {"message": "..."}` frames. Five literal strings are treated as progress (`Getting Google credentials...`, `Fetching Search Console...`, `Scraping website...`, `Thinking...`, `Completed.`); anything else is the final Markdown result.

## Project structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan
│   ├── api/routes/              # auth, search_console, agents (SSE)
│   ├── agents/weekly_agent.py   # Analysis pipeline + prompt
│   ├── tools/                   # LangChain tool wrappers
│   ├── services/                # OAuth, JWT, Search Console, scraper
│   ├── models/                  # User, OAuthAccount, OAuthCredential, Session
│   ├── dependencies/auth.py     # Cookie/JWT authentication
│   ├── db/                      # Async engine + docker-compose
│   └── alembic/                 # Migration history
└── frontend/
    ├── src/app/                 # App Router: landing, callback, dashboard
    ├── src/components/          # Site selector, analysis display, UI primitives
    └── src/lib/                 # API client, auth helpers, config, types
```

## Data model

```
users 1 ── * oauth_accounts 1 ── 1 oauth_credentials
  └── * sessions
```

`oauth_credentials` holds the Google access token, refresh token, and expiry for each linked account. `sessions` holds this application's own session state: a hashed refresh token, expiry, and revocation flag. The two are deliberately separate.

## Known limitations

This is a working project, not a hardened production deployment. Contributions welcome on any of these:

- `GET /agent/weekly` takes `user_id` as a query parameter and does not apply the cookie authentication dependency, so it neither verifies the caller nor checks that the requested site belongs to them.
- Auth cookies are set with `secure=False`, which is fine over local HTTP but unsuitable for an HTTPS deployment.
- Google access and refresh tokens are stored as plain columns rather than encrypted at rest.
- The SSE protocol is untyped: progress versus result is decided by literal string matching, so changing backend wording changes UI classification.
- The Alembic revision graph drops and recreates `sessions` across revisions; reconcile against a deployed schema before upgrading an existing database.

## Contributing

Issues and pull requests are welcome.

1. Fork the repository and create a branch from `main`.
2. Keep the layering intact: HTTP in `api/`, business and provider logic in `services/`, agent-callable adapters in `tools/`, workflow orchestration in `agents/`.
3. Run `uv run alembic revision --autogenerate -m "..."` for any model change.
4. Verify with `npx tsc --noEmit` and `npm run lint` in `frontend/`.
5. Open a PR describing the change and how you tested it.

## Authors

Built by [Muhammad Usman](https://github.com/muhmdusman) and [Muhaddis](https://github.com/Muhaddis-igis).

## License

Released under the [MIT License](LICENSE).

## Topics

`ai-seo-agent` `seo` `seo-tools` `google-search-console` `ai-agent` `llm` `langchain` `mistral-ai` `fastapi` `nextjs` `react` `typescript` `python` `postgresql` `sqlalchemy` `oauth2` `server-sent-events` `tailwindcss` `seo-automation` `search-console-api`
