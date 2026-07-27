from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.entities import StyleTemplate
from backend.services.ecommerce_prompt_service import EcommercePromptService
from backend.services.task_service import TaskService


class EcommerceGenerationService:
    def __init__(self, *, task_service: TaskService) -> None:
        self.task_service = task_service
        self.prompt_service = EcommercePromptService()

    def options(self) -> dict:
        return self.prompt_service.options()

    def create_generation(
        self,
        db: Session,
        *,
        image_id: str,
        template_id: str,
        industry: str,
        brand_tone: str,
        count: int,
        extra_prompt: str = "",
    ):
        composed = self.prompt_service.compose(
            template_id=template_id,
            industry=industry,
            brand_tone=brand_tone,
            extra_prompt=extra_prompt,
        )
        style_id = f"ecommerce_{template_id}_{industry}_{brand_tone}"
        style_name = f"电商图 - {composed.template_name} / {composed.industry_name} / {composed.brand_tone_name}"

        style = db.get(StyleTemplate, style_id)
        if style:
            style.name = style_name
            style.prompt = composed.prompt
            style.negative_prompt = composed.negative_prompt
            style.workflow_json = composed.workflow_json
        else:
            db.add(
                StyleTemplate(
                    id=style_id,
                    name=style_name,
                    prompt=composed.prompt,
                    negative_prompt=composed.negative_prompt,
                    workflow_json=composed.workflow_json,
                )
            )
        db.commit()

        task = self.task_service.create_task(db, image_id=image_id, style_id=style_id, count=count)
        return task, composed
