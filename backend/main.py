from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from app.api.routes.auth import router as auth_router


app = FastAPI()
app.include_router(auth_router)


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{app.title} API Reference",
    )


@app.get("/health")
def health():
    return {"status": "ok"}



def main():
    print("Hello from backend!")



if __name__ == "__main__":
    main()
