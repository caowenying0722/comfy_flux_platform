from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    image_id: str
    filename: str


class GenerateRequest(BaseModel):
    image_id: str
    style_id: str
    count: int = Field(default=5, ge=1, le=20)


class GenerateResponse(BaseModel):
    task_id: str
    status: str


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
