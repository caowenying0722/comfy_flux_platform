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
        "prompt": "cinematic portrait, professional photography, dramatic lighting, shallow depth of field, natural skin texture, high detail, film still, tasteful color grading",
        "negative_prompt": "low quality, worst quality, blurry, jpeg artifacts, watermark, text, logo, deformed, bad anatomy, bad hands, distorted face",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "product",
        "name": "商业摄影",
        "prompt": "premium commercial photography, clean studio lighting, sharp details, elegant composition, high-end advertising, polished surface, realistic shadows",
        "negative_prompt": "low quality, worst quality, cluttered background, blurry, jpeg artifacts, watermark, text, logo, distorted object",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "anime",
        "name": "动漫风",
        "prompt": "anime style illustration, clean line art, vibrant colors, expressive eyes, detailed background, polished digital art, beautiful lighting",
        "negative_prompt": "low quality, worst quality, blurry, jpeg artifacts, watermark, text, logo, deformed, extra limbs, bad hands",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "figurine3d",
        "name": "3D手办",
        "prompt": "3D collectible figurine, toy photography, premium resin material, detailed sculpt, studio lighting, miniature diorama, smooth high quality render",
        "negative_prompt": "low quality, worst quality, blurry, jpeg artifacts, watermark, text, logo, broken model, malformed body",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "guofeng",
        "name": "国风艺术",
        "prompt": "traditional Chinese art style, elegant guofeng aesthetics, ink wash details, refined composition, soft silk texture, poetic atmosphere",
        "negative_prompt": "low quality, worst quality, blurry, jpeg artifacts, watermark, text, logo, messy composition, distorted face",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "oilpainting",
        "name": "油画风",
        "prompt": "oil painting portrait, rich brush strokes, museum quality, dramatic lighting, detailed canvas texture, classical composition",
        "negative_prompt": "low quality, worst quality, blurry, jpeg artifacts, watermark, text, logo, flat colors, distorted anatomy",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "sd15_legacy",
        "name": "SD1.5 兼容生图",
        "prompt": "high quality, detailed, professional photography, clean composition",
        "negative_prompt": "low quality, blurry, distorted, watermark, text, bad anatomy",
        "workflow_json": "sd15_img2img.json",
    },
    {
        "id": "sdxl_base",
        "name": "SDXL 高质量兼容",
        "prompt": "masterpiece, best quality, high quality, ultra detailed, professional photography, cinematic lighting, sharp focus, rich detail, elegant composition",
        "negative_prompt": "low quality, worst quality, blurry, jpeg artifacts, watermark, text, logo, deformed, bad anatomy, bad hands, distorted face",
        "workflow_json": "sdxl_base_img2img.json",
    },
    {
        "id": "dreamshaper_pixar",
        "name": "DreamShaper 3D皮克斯风",
        "prompt": "3D Pixar-style character rendering, stylized 3D animated movie look, keep the exact same person or people from the reference image, preserve the correct number of people, preserve each person's identity, face structure, hairstyle, clothing, pose, body shape and position, keep the original background unchanged, keep the original composition, clean high quality 3D animation style, soft lighting, smooth materials, expressive but natural faces, only stylize the people into 3D animated characters",
        "negative_prompt": "extra person, missing person, wrong number of people, changed background, new background, different scene, added objects, removed objects, changed clothing, changed pose, changed hairstyle, changed face identity, duplicate person, cropped person, out of frame, photorealistic, realistic photo, anime, manga, 2d illustration, oil painting, watercolor, sketch, text, watermark, logo, low quality, blurry, distorted face, deformed body, bad anatomy, bad hands, extra fingers, missing fingers",
        "workflow_json": "dreamshaper_xl_img2img.json",
    },
    {
        "id": "pixar_controlnet",
        "name": "ControlNet 3D皮克斯风",
        "prompt": "3D Pixar-style animated movie still, stylized 3D cartoon character, cute and expressive face, large friendly eyes, rounded facial features, soft smooth materials, warm cinematic lighting, colorful but natural, high quality 3D animation render, preserve the same person or people, preserve the correct number of people, preserve hairstyle, clothing, pose and body position, keep the original background unchanged, keep the original composition, horizontal 3:2 image",
        "negative_prompt": "extra person, missing person, wrong number of people, duplicate person, changed background, new background, different scene, added objects, removed objects, changed clothing, changed pose, changed hairstyle, changed face identity, cropped person, out of frame, photorealistic, realistic photo, anime, manga, 2d illustration, sketch, oil painting, watercolor, text, watermark, logo, low quality, blurry, distorted face, deformed body, bad anatomy, bad hands, extra fingers, missing fingers",
        "workflow_json": "pixar_controlnet_img2img.json",
    },
]

DEPRECATED_STYLE_IDS = {"flux_schnell"}


class PromptService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def seed_defaults(self, db: Session) -> None:
        for style_id in DEPRECATED_STYLE_IDS:
            style = db.get(StyleTemplate, style_id)
            if style:
                db.delete(style)
        for item in DEFAULT_STYLES:
            style = db.get(StyleTemplate, item["id"])
            if style:
                style.name = item["name"]
                style.prompt = item["prompt"]
                style.negative_prompt = item["negative_prompt"]
                style.workflow_json = item["workflow_json"]
            else:
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
