from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    image_id: str
    filename: str


class BatchUploadResponse(BaseModel):
    images: list[UploadResponse]


class GenerateRequest(BaseModel):
    image_id: str
    style_id: str
    count: int = Field(default=5, ge=1, le=20)


class GenerateResponse(BaseModel):
    task_id: str
    status: str


class EcommerceGenerateRequest(BaseModel):
    image_id: str
    template_id: str = Field(default="commercial_photo")
    industry: str = Field(default="general")
    brand_tone: str = Field(default="premium")
    count: int = Field(default=6, ge=1, le=20)
    extra_prompt: str = Field(default="", max_length=1000)


class EcommerceGenerateResponse(BaseModel):
    task_id: str
    status: str
    style_id: str
    prompt: str
    negative_prompt: str
    workflow_json: str


class EcommerceOption(BaseModel):
    id: str
    name: str
    description: str = ""


class EcommerceOptionsResponse(BaseModel):
    templates: list[EcommerceOption]
    industries: list[EcommerceOption]
    brand_tones: list[EcommerceOption]


class BatchGenerateRequest(BaseModel):
    image_ids: list[str] = Field(min_length=1, max_length=20)
    style_id: str
    count: int = Field(default=1, ge=1, le=20)


class BatchGenerateItem(BaseModel):
    image_id: str
    task_id: str
    status: str


class BatchGenerateResponse(BaseModel):
    tasks: list[BatchGenerateItem]


class VariantGridRequest(BaseModel):
    image_id: str
    style_ids: list[str] | None = Field(default=None, min_length=6, max_length=6)


class VariantGridTask(BaseModel):
    style_id: str
    style_name: str
    task_id: str


class VariantGridResponse(BaseModel):
    id: str
    status: str
    image_id: str
    tasks: list[VariantGridTask]
    grid_url: str | None = None
    error: str | None = None


class VideoKenBurnsRequest(BaseModel):
    image_id: str
    duration: float = Field(default=4.0, ge=1.0, le=15.0)
    fps: int = Field(default=24, ge=8, le=30)
    width: int = Field(default=1152, ge=256, le=1920)
    height: int = Field(default=768, ge=256, le=1080)
    motion: str = Field(default="slow_zoom_in")


class VideoStyleRequest(VideoKenBurnsRequest):
    style_id: str = "pixar_controlnet"


class VideoResponse(BaseModel):
    id: str
    status: str
    kind: str
    image_id: str
    style_id: str | None = None
    generation_task_id: str | None = None
    video_url: str | None = None
    error: str | None = None


class TaskImage(BaseModel):
    item_id: str
    seed: int
    status: str
    url: str | None = None
    error: str | None = None


class TaskResponse(BaseModel):
    id: str
    status: str
    image_id: str
    style_id: str
    count: int
    images: list[TaskImage]
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class StyleResponse(BaseModel):
    id: str
    name: str
    prompt: str
    negative_prompt: str
    workflow_json: str
