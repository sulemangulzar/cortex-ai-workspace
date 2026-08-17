from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.core.exceptions import ServiceError


app = FastAPI()
app.include_router(auth_router)


@app.exception_handler(ServiceError)
async def service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    """Keep the legacy docs URL working without a mandatory Scalar import."""
    return {"docs_url": "/docs", "message": "Use FastAPI's built-in API docs"}


@app.get("/health")
def health():
    return {"status": "ok"}



def main():
    print("Hello from backend!")



if __name__ == "__main__":
    main()
