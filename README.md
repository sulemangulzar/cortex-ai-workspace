# Cortex AI Workspace

A focused AI workspace for turning ideas, documents, chat, and generated code into structured projects.

## Recommended Product Name

**Cortex Studio** is the strongest name for this app. It keeps the existing Cortex identity, sounds polished, and makes the product feel like a place where AI-assisted work is created and refined.

Other good options:

- **Cortex Forge**
- **Clearspace AI**
- **Mindframe Studio**

## Project Structure

- `frontend/` - React + Vite app, ready for Vercel static deployment.
- `backend/` - FastAPI API, database models, migrations, auth, chat, realtime, and project services.

## Vercel Deployment

This repository is configured so Vercel can deploy the frontend from `frontend/`.

1. Push this repository to GitHub.
2. In Vercel, create a new project from the repo.
3. Set **Root Directory** to `frontend`.
4. Vercel should detect Vite automatically. Confirm these settings:
   - Build Command: `npm run build`
   - Install Command: `npm ci`
   - Output Directory: `dist`
5. Add this environment variable in Vercel:
   - `VITE_API_URL=https://your-backend-domain.com`
6. Deploy.

The frontend needs a deployed API because the app calls FastAPI routes and opens a websocket connection. Vercel static hosting is a good fit for the React app; deploy the FastAPI backend separately on a service such as Render, Railway, Fly.io, or a VPS.

## Backend Production Notes

Set these backend environment variables on your API host:

- `DATABASE_URL`
- `FRONTEND_URL=https://your-vercel-app.vercel.app`
- `JWT_SECRET_KEY`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=none`
- `OPENAI_API_KEY`
- `SUPABASE_S3_ENDPOINT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `BUCKET_NAME`

Run database migrations before using the production API:

```bash
cd backend
alembic upgrade head
```

## Local Development

Start the backend:

```bash
cd backend
uv run fastapi dev main.py
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```
