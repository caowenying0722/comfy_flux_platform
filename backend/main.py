import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router, task_service
from backend.core.config import get_settings
from backend.database.session import Base, SessionLocal, engine
from backend.services.prompt_service import PromptService


settings = get_settings()
app = FastAPI(title=settings.app_name)


@app.on_event("startup")
async def startup() -> None:
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.workflow_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite:///")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        PromptService().seed_defaults(db)
    asyncio.create_task(task_service.worker_loop())


@app.get("/health")
def health():
    return {"status": "ok", "comfyui": task_service.comfyui.healthcheck()}


@app.get("/")
def index():
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "apis": {
            "upload": "POST /upload",
            "generate": "POST /generate",
            "task": "GET /task/{id}",
            "styles": "GET /styles",
            "files": "GET /files/{path}",
        },
    }


app.include_router(router)
app.mount("/files", StaticFiles(directory=settings.storage_root), name="files")
