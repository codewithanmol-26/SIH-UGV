"""
UGV Mission Console backend — entry point.

Run with:  uvicorn main:app --reload --port 8000   (from the backend/ directory)
or simply: python main.py
"""
from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Allow `import config...`, `import perception...` etc. regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from api.routes import router as api_router
from api.websocket import telemetry_websocket
from communication.state_manager import NavigationSystem


@asynccontextmanager
async def lifespan(app: FastAPI):
    nav = NavigationSystem()
    app.state.navigation_system = nav
    await nav.initialize()
    loop_task = asyncio.create_task(nav.run_forever(hz=10.0))
    try:
        yield
    finally:
        nav.stop_loop()
        loop_task.cancel()


app = FastAPI(
    title="UGV Mission Console API",
    description=(
        "Backend for Smart India Hackathon PS 26126 — Vision Based Autonomous "
        "Navigation for an Unmanned Ground Vehicle. See /docs for the interactive "
        "API reference and docs/api.md in the repo for the WebSocket protocol."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket):
    await telemetry_websocket(websocket)


@app.get("/")
async def root():
    return {
        "service": "ugv-mission-console-backend",
        "docs": "/docs",
        "websocket": "/ws/telemetry",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
