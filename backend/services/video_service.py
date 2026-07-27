import json
import math
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from backend.models.entities import GenerationTask, UploadedImage
from backend.services.storage import StorageService
from backend.services.task_service import TaskService


class VideoService:
    def __init__(self, *, task_service: TaskService) -> None:
        self.task_service = task_service
        self.storage = StorageService()

    def create_kenburns_video(
        self,
        db: Session,
        *,
        image_id: str,
        duration: float = 4.0,
        fps: int = 24,
        width: int = 1152,
        height: int = 768,
        motion: str = "slow_zoom_in",
    ) -> dict:
        image = db.get(UploadedImage, image_id)
        if not image:
            raise ValueError("image_id not found")

        video_id = str(uuid4())
        manifest = {
            "id": video_id,
            "status": "generating",
            "kind": "kenburns",
            "image_id": image_id,
            "style_id": None,
            "generation_task_id": None,
            "motion": motion,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "video_path": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._write_manifest(video_id, manifest)
        try:
            output_path = self._render_kenburns(Path(image.path), video_id, duration, fps, width, height, motion)
            manifest["status"] = "completed"
            manifest["video_path"] = str(output_path)
            manifest["updated_at"] = datetime.utcnow().isoformat()
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = str(exc)
            manifest["updated_at"] = datetime.utcnow().isoformat()
        self._write_manifest(video_id, manifest)
        return manifest

    def create_styled_video(
        self,
        db: Session,
        *,
        image_id: str,
        style_id: str,
        duration: float = 4.0,
        fps: int = 24,
        width: int = 1152,
        height: int = 768,
        motion: str = "slow_zoom_in",
    ) -> dict:
        task = self.task_service.create_task(db, image_id=image_id, style_id=style_id, count=1)
        video_id = str(uuid4())
        manifest = {
            "id": video_id,
            "status": "pending",
            "kind": "styled",
            "image_id": image_id,
            "style_id": style_id,
            "generation_task_id": task.id,
            "motion": motion,
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "video_path": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._write_manifest(video_id, manifest)
        return manifest

    def get_video(self, db: Session, video_id: str) -> dict | None:
        manifest = self._read_manifest(video_id)
        if not manifest:
            return None
        if manifest["status"] in {"completed", "failed"}:
            return manifest

        if manifest["kind"] != "styled":
            return manifest

        task = db.get(GenerationTask, manifest["generation_task_id"])
        if not task:
            manifest["status"] = "failed"
            manifest["error"] = "generation task not found"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(video_id, manifest)
            return manifest

        if task.status in {"pending", "generating"}:
            manifest["status"] = "generating"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(video_id, manifest)
            return manifest

        if task.status != "completed":
            manifest["status"] = "failed"
            manifest["error"] = task.error or "generation task failed"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(video_id, manifest)
            return manifest

        completed_items = [item for item in task.items if item.status == "completed" and item.output_path]
        if not completed_items:
            manifest["status"] = "failed"
            manifest["error"] = "generation completed without output image"
            manifest["updated_at"] = datetime.utcnow().isoformat()
            self._write_manifest(video_id, manifest)
            return manifest

        try:
            output_path = self._render_kenburns(
                Path(completed_items[0].output_path),
                video_id,
                float(manifest["duration"]),
                int(manifest["fps"]),
                int(manifest["width"]),
                int(manifest["height"]),
                manifest["motion"],
            )
            manifest["status"] = "completed"
            manifest["video_path"] = str(output_path)
            manifest["updated_at"] = datetime.utcnow().isoformat()
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = str(exc)
            manifest["updated_at"] = datetime.utcnow().isoformat()
        self._write_manifest(video_id, manifest)
        return manifest

    def _render_kenburns(
        self,
        image_path: Path,
        video_id: str,
        duration: float,
        fps: int,
        width: int,
        height: int,
        motion: str,
    ) -> Path:
        frame_count = max(2, int(duration * fps))
        source = Image.open(image_path).convert("RGB")
        frames = [self._frame(source, i, frame_count, width, height, motion) for i in range(frame_count)]

        gif_path = self.storage.video_path(video_id, ".gif")
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0,
            optimize=True,
        )
        return gif_path

    def _frame(self, source: Image.Image, index: int, frame_count: int, width: int, height: int, motion: str):
        progress = index / max(1, frame_count - 1)
        eased = 0.5 - 0.5 * math.cos(progress * math.pi)

        base = self._cover(source, width, height)
        zoom = 1.0 + 0.08 * eased
        if motion == "slow_zoom_out":
            zoom = 1.08 - 0.08 * eased
        elif motion == "pan_left":
            zoom = 1.06
        elif motion == "pan_right":
            zoom = 1.06

        zoom_w = int(width * zoom)
        zoom_h = int(height * zoom)
        enlarged = base.resize((zoom_w, zoom_h), Image.Resampling.LANCZOS)

        max_x = max(0, zoom_w - width)
        max_y = max(0, zoom_h - height)
        if motion == "pan_left":
            left = int(max_x * (1 - eased))
            top = max_y // 2
        elif motion == "pan_right":
            left = int(max_x * eased)
            top = max_y // 2
        else:
            left = max_x // 2
            top = max_y // 2

        frame = enlarged.crop((left, top, left + width, top + height))
        return self._add_subtle_vignette(frame)

    def _cover(self, source: Image.Image, width: int, height: int) -> Image.Image:
        src_w, src_h = source.size
        scale = max(width / src_w, height / src_h)
        resized = source.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - width) // 2
        top = (resized.height - height) // 2
        return resized.crop((left, top, left + width, top + height))

    def _add_subtle_vignette(self, frame: Image.Image) -> Image.Image:
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = frame.size
        for i in range(24):
            alpha = int(i * 1.6)
            draw.rectangle((i, i, w - i - 1, h - i - 1), outline=(0, 0, 0, alpha))
        return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")

    def _read_manifest(self, video_id: str) -> dict | None:
        path = self.storage.video_manifest_path(video_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_manifest(self, video_id: str, manifest: dict) -> None:
        path = self.storage.video_manifest_path(video_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
