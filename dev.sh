#!/usr/bin/env bash
#
# Search Console Agent - full stack development launcher
#
# Starts PostgreSQL, Redis, Adminer, the Celery worker, the FastAPI API,
# and the Next.js frontend. Ctrl+C stops everything.
#
# Works on Linux, macOS, and Windows via Git Bash or WSL.
# Native Windows users without bash should run dev.ps1 instead.

set -euo pipefail

# Run from the repository root no matter where the script is invoked from.
cd "$(dirname "${BASH_SOURCE[0]}")"
ROOT_DIR="$(pwd)"

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

IS_WINDOWS=0
case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) IS_WINDOWS=1 ;;
esac

# Force UTF-8 for Python stdout/stderr. On Windows the console defaults to a
# legacy codepage (cp1252), where logging any non-ASCII character raises
# UnicodeEncodeError. No effect on Linux/macOS, which are UTF-8 already.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
ok()   { printf '    [ok] %s\n' "$*"; }
warn() { printf '    [!] %s\n' "$*"; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

step "Checking prerequisites"

need() {
    command -v "$1" >/dev/null 2>&1 || die "'$1' not found on PATH. $2"
}

need docker "Install Docker Desktop or Docker Engine."
need uv     "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
need npm    "Install Node.js 20 or newer: https://nodejs.org/"

# Prefer the v2 plugin, fall back to the standalone v1 binary.
if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    die "Neither 'docker compose' nor 'docker-compose' is available."
fi

docker info >/dev/null 2>&1 || die "Docker is installed but not running. Start Docker and retry."

ok "docker, uv, npm present"

# ---------------------------------------------------------------------------
# Environment file
# ---------------------------------------------------------------------------
# The backend reads ./.env relative to its own working directory, so
# backend/.env has to exist. A root .env is the shared source of truth when
# present, but a standalone backend/.env is equally valid.

step "Resolving environment file"

if [ -f "$ROOT_DIR/.env" ]; then
    if [ "$IS_WINDOWS" -eq 1 ]; then
        # Symlinks on Windows need Developer Mode or elevation, so copy instead.
        cp -f "$ROOT_DIR/.env" "$ROOT_DIR/backend/.env"
        ok "copied root .env to backend/.env"
    else
        ln -sfn ../.env "$ROOT_DIR/backend/.env"
        ok "linked backend/.env to root .env"
    fi
elif [ -f "$ROOT_DIR/backend/.env" ]; then
    ok "using existing backend/.env"
else
    die "No .env found. Create one at $ROOT_DIR/.env (see the README for the
       required keys), or place it directly at backend/.env."
fi

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

step "Starting PostgreSQL, Redis, and Adminer"

"${COMPOSE[@]}" -f "$ROOT_DIR/backend/docker-compose.yaml" up -d

wait_for_health() {
    local container="$1" attempts=60 status
    printf '    waiting for %s' "$container"
    while [ "$attempts" -gt 0 ]; do
        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
            "$container" 2>/dev/null || echo missing)"
        case "$status" in
            healthy | running)
                printf ' ready\n'
                return 0
                ;;
            missing)
                printf '\n'
                die "Container '$container' was not created. Check: ${COMPOSE[*]} logs"
                ;;
        esac
        printf '.'
        sleep 1
        attempts=$((attempts - 1))
    done
    printf '\n'
    die "Container '$container' never became healthy. Check: docker logs $container"
}

wait_for_health postgres
wait_for_health redis

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

step "Installing Python dependencies"
( cd "$ROOT_DIR/backend" && uv sync )
ok "dependencies synced"

step "Applying database migrations"
if ( cd "$ROOT_DIR/backend" && uv run alembic upgrade head ); then
    ok "schema up to date"
else
    die "Migrations failed. Fix the error above before continuing."
fi

# Track every process we spawn so cleanup can stop all of them.
PIDS=()

# macOS still ships bash 3.2, which has no negative array indexing.
last_pid() { printf '%s' "${PIDS[$((${#PIDS[@]} - 1))]}"; }

step "Starting Celery worker"
# The default prefork pool relies on fork(), which Windows does not provide.
CELERY_ARGS=(-A core.celery_app worker --loglevel=info)
if [ "$IS_WINDOWS" -eq 1 ]; then
    CELERY_ARGS+=(--pool=solo)
    warn "using --pool=solo (Windows has no fork; concurrency is 1)"
else
    CELERY_ARGS+=(--concurrency=2)
fi

( cd "$ROOT_DIR/backend" && exec uv run celery "${CELERY_ARGS[@]}" ) \
    > "$ROOT_DIR/backend/celery.log" 2>&1 &
PIDS+=($!)
ok "celery worker (pid $(last_pid)), logging to backend/celery.log"

step "Starting FastAPI"
( cd "$ROOT_DIR/backend" && exec uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload ) \
    > "$ROOT_DIR/backend/backend.log" 2>&1 &
PIDS+=($!)
ok "api (pid $(last_pid)), logging to backend/backend.log"

printf '    waiting for api'
API_READY=0
for _ in $(seq 1 45); do
    if curl -fsS -o /dev/null "http://127.0.0.1:8000/openapi.json" 2>/dev/null; then
        API_READY=1
        printf ' ready\n'
        break
    fi
    printf '.'
    sleep 1
done
if [ "$API_READY" -eq 0 ]; then
    printf '\n'
    warn "api did not respond within 45s; see backend/backend.log"
fi

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

step "Starting Next.js frontend"

if [ ! -f "$ROOT_DIR/frontend/.env.local" ]; then
    printf 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1\n' \
        > "$ROOT_DIR/frontend/.env.local"
    ok "created frontend/.env.local"
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
    say "    installing npm packages (first run, this takes a minute)"
    ( cd "$ROOT_DIR/frontend" && npm install )
fi

( cd "$ROOT_DIR/frontend" && exec npm run dev ) > "$ROOT_DIR/frontend.log" 2>&1 &
PIDS+=($!)
ok "frontend (pid $(last_pid)), logging to frontend.log"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

CLEANED=0
cleanup() {
    [ "$CLEANED" -eq 1 ] && return 0
    CLEANED=1
    trap - INT TERM EXIT

    step "Stopping services"

    for pid in "${PIDS[@]}"; do
        kill_tree "$pid"
    done

    "${COMPOSE[@]}" -f "$ROOT_DIR/backend/docker-compose.yaml" down

    say ""
    ok "all services stopped"
    exit 0
}

# Dev servers spawn children (uvicorn's reloader, next's compiler). Killing
# only the parent would orphan them and leave ports 8000 and 3000 occupied.
# Depth first so children die before the parent that would otherwise respawn
# or reparent them.
kill_tree() {
    local pid="$1" child

    if command -v pgrep >/dev/null 2>&1; then
        for child in $(pgrep -P "$pid" 2>/dev/null || true); do
            kill_tree "$child"
        done
    fi

    kill "$pid" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

# ---------------------------------------------------------------------------
# Ready
# ---------------------------------------------------------------------------

cat <<'BANNER'

===========================================================
  Search Console Agent is running
===========================================================

  Frontend    http://localhost:3000
  API         http://127.0.0.1:8000
  API docs    http://127.0.0.1:8000/docs
  Adminer     http://localhost:8081

  PostgreSQL  localhost:5433
  Redis       localhost:6379

  Logs        backend/backend.log
              backend/celery.log
              frontend.log

  Press Ctrl+C to stop everything.
===========================================================

BANNER

wait
