from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.research import router as research_router
from app.api.qa import router as qa_router
from app.api.export import router as export_router

app = FastAPI(
    title="PHSS Research Assistant",
    description="Multi-Agent Research Pipeline API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router, prefix="/api")
app.include_router(qa_router,       prefix="/api")
app.include_router(export_router,   prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PHSS Research Assistant"}
