import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from backend.models.entities import GenerationTask, UploadedImage
from backend.services.prompt_service import PromptService
from backend.services.storage import StorageService
from backend.services.task_service import TaskService


DEFAULT_VARIANT_STYLE_IDS = [
    "pixar_controlnet",
    "dreamshaper_pixar",
    "anime",
    "figurine3d",
    "guofeng",
    "oilpainting",
]


class VariantService:
    def __init__(self, *, task_service: TaskService) -> None:
        self.task_service = task_service
        self.storage = StorageService()
        self.prompt_service = PromptService()

    def create_variant_grid(
        self,
        db: Session,
        *,
        image_id: str,
        style_ids: list[str] | None = None,
    ) -> dict:
        if not db.get(UploadedImage, image_id):
            raise ValueError("image_id not found")

        selected_style_ids = style_ids or DEFAULT_VARIANT_STYLE_IDS
        if len(selected_style_ids) != 6:
            raise ValueError("variant grid requires exactly 6 style_ids")

        tasks = []
        for style_id in selected_style_ids:
            style = self.prompt_service.get_style(db, style_id)
            if not style:
                raise ValueError(f"style_id not found: {style_id}")
            task = self.task_service.create_task(db, image_id=image_id, style_id=style_id, count=1)
            tasks.append(
                {
                    "style_id": style_id,
                    "style_name": style.name,
                    "task_id": task.id,
                }
            )

        variant_id = str(uuid4())
        manifest = {
            "id": variant_id,
            "status": "pending",
            "image_id": image_id,
            "tasks": tasks,
            "grid_path": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._write_manifest(variant_id, manifest)
        return manifest

    def get_variant_grid(self, db: Session, variant_id: str) -> dict | None:
        manifest = self._read_manifest(variant_id)
        if not manifest:
            return None

        if manifest["status"] in {"completed", "failed"}:
            return manifest

        task_rows = []
        for item in manifest["tasks"]:
            task = db.get(GenerationTask, item["task_id"])
            if task:
                task_rows.append(task)

        if len(task_rows) != len(manifest["tasks"]):
            manifest["status"] = "failed"
            manifest["error"] = "one or more tasks were not found"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(variant_id, manifest)
            return manifest

        statuses = [task.status for task in task_rows]
        if any(status in {"pending", "generating"} for status in statuses):
            manifest["status"] = "generating" if any(status == "generating" for status in statuses) else "pending"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(variant_id, manifest)
            return manifest

        if not all(status == "completed" for status in statuses):
            manifest["status"] = "failed"
            manifest["error"] = "one or more variant tasks failed"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(variant_id, manifest)
            return manifest

        try:
            grid_path = self._build_grid(manifest, task_rows)
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = str(exc)
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(variant_id, manifest)
            return manifest

        manifest["status"] = "completed"
        manifest["grid_path"] = str(grid_path)
        manifest["updated_at"] = datetime.utcnow().isoformat()
        self._write_manifest(variant_id, manifest)
        return manifest

    def _build_grid(self, manifest: dict, task_rows: list[GenerationTask]) -> Path:
        cells: list[tuple[str, Path]] = []
        task_map = {task.id: task for task in task_rows}
        for item in manifest["tasks"]:
            task = task_map[item["task_id"]]
            completed_items = [task_item for task_item in task.items if task_item.status == "completed" and task_item.output_path]
            if not completed_items:
                raise RuntimeError(f"task has no completed image: {task.id}")
            cells.append((item["style_id"], Path(completed_items[0].output_path)))

        cell_w, cell_h = 512, 512
        label_h = 56
        margin = 20
        cols, rows = 3, 2
        canvas_w = cols * cell_w + (cols + 1) * margin
        canvas_h = rows * (cell_h + label_h) + (rows + 1) * margin
        canvas = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()

        for index, (label, path) in enumerate(cells):
            col = index % cols
            row = index // cols
            x = margin + col * (cell_w + margin)
            y = margin + row * (cell_h + label_h + margin)
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                image_x = x + (cell_w - img.width) // 2
                image_y = y + (cell_h - img.height) // 2
                canvas.paste(img, (image_x, image_y))
            draw.rectangle((x, y + cell_h, x + cell_w, y + cell_h + label_h), fill=(255, 255, 255))
            draw.text((x + 12, y + cell_h + 18), label, fill=(20, 20, 20), font=font)

        output_path = self.storage.variant_grid_path(manifest["id"])
        canvas.save(output_path, quality=92)
        return output_path

    def _read_manifest(self, variant_id: str) -> dict | None:
        path = self.storage.variant_manifest_path(variant_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_manifest(self, variant_id: str, manifest: dict) -> None:
        path = self.storage.variant_manifest_path(variant_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
