from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference

from app.api.routes.project import router as project_router
from app.api.routes.realtime import router as realtime_router
from app.api.routes.run import router as run_router
from app.api.routes.chat import router as chat_router
from app.api.routes.auth import router as auth_router
from app.core.database import engine
from app.core.config import settings
from app.core.exceptions import ServiceError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    if engine is not None:
        await engine.dispose()


app = FastAPI(title="Cortex Studio API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://127.0.0.1:5173"],
    # Vite may move to another local port when 5173 is occupied.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(run_router)
app.include_router(realtime_router)
app.include_router(chat_router)


@app.exception_handler(ServiceError)
async def service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{app.title} API Reference",
    )


@app.get("/health")
def health():
    return {"status": "ok"}
