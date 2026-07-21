import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.entities import StyleTemplate


DEFAULT_STYLES = [
    {
        "id": "cinematic",
        "name": "电影写真",
        "prompt": "cinematic portrait, professional photography, dramatic lighting, ultra detailed, natural skin texture",
        "negative_prompt": "low quality, blurry, distorted, extra fingers, bad anatomy, watermark",
        "workflow_json": "cinematic.json",
    },
    {
        "id": "product",
        "name": "商业摄影",
        "prompt": "premium commercial photography, clean studio lighting, sharp details, elegant composition, high-end advertising",
        "negative_prompt": "low quality, cluttered background, blurry, watermark, text",
        "workflow_json": "product.json",
    },
    {
        "id": "anime",
        "name": "动漫风",
        "prompt": "anime style illustration, clean line art, vibrant colors, expressive eyes, detailed background",
        "negative_prompt": "low quality, blurry, deformed, extra limbs, watermark",
        "workflow_json": "anime.json",
    },
    {
        "id": "figurine3d",
        "name": "3D手办",
        "prompt": "3D collectible figurine, toy photography, premium resin material, detailed sculpt, studio lighting",
        "negative_prompt": "low quality, blurry, broken model, watermark, text",
        "workflow_json": "figurine3d.json",
    },
    {
        "id": "guofeng",
        "name": "国风艺术",
        "prompt": "traditional Chinese art style, elegant guofeng aesthetics, ink wash details, refined composition",
        "negative_prompt": "low quality, blurry, messy, watermark, text",
        "workflow_json": "guofeng.json",
    },
    {
        "id": "oilpainting",
        "name": "油画风",
        "prompt": "oil painting portrait, rich brush strokes, museum quality, dramatic lighting, detailed texture",
        "negative_prompt": "low quality, blurry, flat colors, watermark, text",
        "workflow_json": "oilpainting.json",
    },
]


class PromptService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def seed_defaults(self, db: Session) -> None:
        for item in DEFAULT_STYLES:
            if not db.get(StyleTemplate, item["id"]):
                db.add(StyleTemplate(**item))
        db.commit()

    def list_styles(self, db: Session) -> list[StyleTemplate]:
        return db.query(StyleTemplate).order_by(StyleTemplate.created_at.asc()).all()

    def get_style(self, db: Session, style_id: str) -> StyleTemplate | None:
        return db.get(StyleTemplate, style_id)

    def load_workflow(self, style: StyleTemplate) -> dict[str, Any]:
        workflow_path = self.settings.workflow_dir / style.workflow_json
        with workflow_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def render_workflow(
        self,
        workflow: dict[str, Any],
        *,
        input_image: str,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        upscale_factor: int,
    ) -> dict[str, Any]:
        values = {
            "{{input_image}}": input_image,
            "{{prompt}}": prompt,
            "{{negative_prompt}}": negative_prompt,
            "{{seed}}": seed,
            "{{width}}": width,
            "{{height}}": height,
            "{{upscale_factor}}": upscale_factor,
        }

        def replace(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: replace(v) for k, v in obj.items() if k != "_meta"}
            if isinstance(obj, list):
                return [replace(v) for v in obj]
            if isinstance(obj, str):
                if obj in values:
                    return values[obj]
                for key, value in values.items():
                    obj = obj.replace(key, str(value))
                return obj
            return obj

        return replace(workflow)
