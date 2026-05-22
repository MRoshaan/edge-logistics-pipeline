from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.services.database import close_database, ping_database
from app.settings import get_settings

settings = get_settings()

app = FastAPI(title="Fleet Edge API", version="0.1.0")


@app.on_event("startup")
async def startup_event() -> None:
    await ping_database()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await close_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
