from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.database import connect_db, close_db
from app.api import auth, sessions, kyc, videos, admin, websocket, notifications

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    logger.info("✅ Sync API ready")
    yield
    await close_db()


app = FastAPI(
    title="Sync API",
    description="Mutual Interaction Recording & Safety Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,          prefix="/api/auth",          tags=["Auth"])
app.include_router(sessions.router,      prefix="/api/sessions",      tags=["Sessions"])
app.include_router(kyc.router,           prefix="/api/kyc",           tags=["KYC"])
app.include_router(videos.router,        prefix="/api/videos",        tags=["Videos"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(admin.router,         prefix="/api/admin",         tags=["Admin"])
app.include_router(websocket.router,     prefix="",                   tags=["WebSocket"])


@app.get("/")
async def root():
    return {"message": "Sync API v1.0", "status": "operational", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
