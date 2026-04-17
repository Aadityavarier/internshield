"""
InternShield — FastAPI Backend

AI-powered fake internship offer letter detector.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers.analyze import router as analyze_router

load_dotenv()

app = FastAPI(
    title="InternShield API",
    description="AI-powered fake internship/job offer letter detector",
    version="1.0.0",
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(analyze_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "InternShield API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "analyze": "/api/analyze",
            "history": "/api/history/{session_id}",
            "health": "/api/health",
        },
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}
