# Cortex Studio API

FastAPI backend for Cortex Studio.

## Why This Should Not Run On Vercel Serverless

This backend uses authenticated websocket routes and long-running AI pipeline work. Vercel is a strong fit for the Vite frontend, but the backend should run as a persistent ASGI service on Render, Railway, Fly.io, a VPS, or another container/Python web service host.

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
