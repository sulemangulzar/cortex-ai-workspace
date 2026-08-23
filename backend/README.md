# Cortex Studio API

FastAPI backend for Cortex Studio.

## Vercel Deployment

This backend is configured for Vercel's FastAPI Python runtime through `vercel.json` and `[tool.vercel]` in `pyproject.toml`.

Vercel can run the HTTP FastAPI routes as a Python Function. The app still contains websocket routes and long-running agent pipeline work, so production behavior should be tested carefully after deploy. The frontend includes polling fallback so project/activity updates can still refresh when websockets are unavailable.

## Deploy On Vercel

1. Create a new Vercel project from this repo.
2. Set **Root Directory** to `backend`.
3. Leave Build Command and Output Directory empty unless Vercel asks for them.
4. Add the environment variables from `.env.example`.
5. Deploy.
6. Run migrations from your machine or a temporary shell with the production `DATABASE_URL`:

```bash
cd backend
uv run alembic upgrade head
```

7. Copy the backend deployment URL into the frontend Vercel project:

```env
VITE_API_URL=https://your-backend.vercel.app
```

For cross-domain auth cookies, set:

```env
COOKIE_SECURE=true
COOKIE_SAMESITE=none
FRONTEND_URL=https://your-frontend.vercel.app
```

## Persistent Host Alternative

If the agent pipeline regularly exceeds Vercel function limits or websocket behavior matters, deploy this same backend to Render, Railway, Fly.io, a VPS, or another container/Python web service host.

## Production Start Command

```bash
uv run uvicorn main:app --host 0.0.0.0 --port $PORT
```

The included `Procfile` and `Dockerfile` use this command.

## Required Environment Variables

- `DATABASE_URL`
- `FRONTEND_URL`
- `JWT_SECRET_KEY`
- `COOKIE_SECURE`
- `COOKIE_SAMESITE`
- `OPENAI_API_KEY`
- `SUPABASE_S3_ENDPOINT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `BUCKET_NAME`
- `MAX_UPLOAD_SIZE_BYTES`

For a Vercel frontend on a different domain, use:

```env
COOKIE_SECURE=true
COOKIE_SAMESITE=none
FRONTEND_URL=https://your-vercel-app.vercel.app
```

## Deploy On Render

1. Create a new **Web Service** from this repo.
2. Set the root directory to `backend`.
3. Use Python 3.13.
4. Set the build command:

```bash
pip install uv && uv sync --frozen --no-dev
```

5. Set the start command:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port $PORT
```

6. Add the environment variables from `.env.example`.
7. Run migrations after the first deploy:

```bash
uv run alembic upgrade head
```

## Deploy On Railway

1. Create a new service from this repo.
2. Set the service root to `backend`.
3. Railway can use the included `Dockerfile` or the `Procfile`.
4. Add the environment variables from `.env.example`.
5. Run migrations:

```bash
uv run alembic upgrade head
```

## Health Check

Use:

```text
/health
```
