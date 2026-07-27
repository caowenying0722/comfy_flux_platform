from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = self.settings.storage_root
        self.original_dir = self.root / "original_images"
        self.generated_dir = self.root / "generated_images"
        self.variant_dir = self.root / "variant_grids"
        self.original_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.variant_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> tuple[str, Path]:
        image_id = str(uuid4())
        suffix = Path(file.filename or "upload.png").suffix.lower() or ".png"
        target = self.original_dir / f"{image_id}{suffix}"
        with target.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)
        return image_id, target

    def generated_path(self, item_id: str, suffix: str = ".png") -> Path:
        return self.generated_dir / f"{item_id}{suffix}"

    def variant_manifest_path(self, variant_id: str) -> Path:
        return self.variant_dir / f"{variant_id}.json"

    def variant_grid_path(self, variant_id: str) -> Path:
        return self.variant_dir / f"{variant_id}.jpg"

    def public_url_for_path(self, path: str | None) -> str | None:
        if not path:
            return None
        p = Path(path)
        try:
            rel = p.relative_to(self.root)
        except ValueError:
            return None
        return f"/files/{rel.as_posix()}"
