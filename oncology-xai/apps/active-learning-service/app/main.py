"""Active Learning Service — FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import router

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))

app = FastAPI(
    title="LCHAI Active Learning Service",
    version=settings.version,
    description="Pathologist pattern correction + delta training for FuzzyArcLoss V2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name, "version": settings.version}
