import asyncio
import random
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.session import SessionLocal
from backend.models.entities import GenerationItem, GenerationTask, StyleTemplate, UploadedImage
from backend.services.comfyui_client import ComfyUIClient
from backend.services.prompt_service import PromptService
from backend.services.storage import StorageService


class TaskService:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.settings = get_settings()
        self.prompt_service = PromptService()
        self.storage = StorageService()
        self.comfyui = ComfyUIClient()

    def create_task(self, db: Session, *, image_id: str, style_id: str, count: int) -> GenerationTask:
        if not db.get(UploadedImage, image_id):
            raise ValueError("image_id not found")
        if not db.get(StyleTemplate, style_id):
            raise ValueError("style_id not found")

        task = GenerationTask(id=str(uuid4()), image_id=image_id, style_id=style_id, count=count, status="pending")
        db.add(task)
        for _ in range(count):
            db.add(
                GenerationItem(
                    id=str(uuid4()),
                    task_id=task.id,
                    status="pending",
                    seed=random.randint(1, 2_147_483_647),
                )
            )
        db.commit()
        db.refresh(task)
        self.queue.put_nowait(task.id)
        return task

    async def worker_loop(self) -> None:
        while True:
            task_id = await self.queue.get()
            try:
                await asyncio.to_thread(self._process_task, task_id)
            finally:
                self.queue.task_done()

    def _process_task(self, task_id: str) -> None:
        with SessionLocal() as db:
            task = db.get(GenerationTask, task_id)
            if not task:
                return
            task.status = "generating"
            task.updated_at = datetime.utcnow()
            db.commit()

            pending = db.query(GenerationItem).filter(GenerationItem.task_id == task_id).order_by(GenerationItem.created_at.asc()).all()
            for item in pending:
                self._process_item(db, task, item)

            db.refresh(task)
            statuses = [item.status for item in task.items]
            if all(s == "completed" for s in statuses):
                task.status = "completed"
                task.error = None
            elif any(s == "completed" for s in statuses):
                task.status = "completed"
                task.error = "Some images failed; completed images are available."
            else:
                task.status = "failed"
                task.error = "All generation items failed."
            task.updated_at = datetime.utcnow()
            db.commit()

    def _process_item(self, db: Session, task: GenerationTask, item: GenerationItem) -> None:
        image = db.get(UploadedImage, task.image_id)
        style = db.get(StyleTemplate, task.style_id)
        assert image and style

        while item.retry_count <= self.settings.generation_max_retries:
            try:
                item.status = "generating"
                item.updated_at = datetime.utcnow()
                db.commit()

                image_path = Path(image.path)
                comfy_input_name = self.comfyui.upload_image(image_path=image_path)
                workflow = self.prompt_service.load_workflow(style)
                rendered = self.prompt_service.render_workflow(
                    workflow,
                    input_image=comfy_input_name,
                    prompt=style.prompt,
                    negative_prompt=style.negative_prompt,
                    seed=item.seed,
                    width=self.settings.generation_width,
                    height=self.settings.generation_height,
                    upscale_factor=self.settings.upscale_factor,
                )
                suffix = image_path.suffix or ".png"
                output_path = self.storage.generated_path(item.id, suffix)
                self.comfyui.run_workflow(rendered, output_path)

                item.output_path = str(output_path)
                item.status = "completed"
                item.error = None
                item.updated_at = datetime.utcnow()
                db.commit()
                return
            except Exception as exc:
                item.retry_count += 1
                item.error = str(exc)
                item.status = "pending" if item.retry_count <= self.settings.generation_max_retries else "failed"
                item.updated_at = datetime.utcnow()
                db.commit()
