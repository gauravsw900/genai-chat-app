from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

from app.core.config import settings
from app.api import chat, documents, health

logger = structlog.get_logger()

app = FastAPI(
    title="GenAI Chat",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health.router)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup():
    logger.info("starting", model=settings.openai_model)


@app.on_event("shutdown")
async def shutdown():
    logger.info("shutting down")
