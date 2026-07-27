from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import GenerationTask, UploadedImage
from backend.schemas import (
    BatchGenerateItem,
    BatchGenerateRequest,
    BatchGenerateResponse,
    BatchUploadResponse,
    GenerateRequest,
    GenerateResponse,
    StyleResponse,
    TaskImage,
    TaskResponse,
    UploadResponse,
    VariantGridRequest,
    VariantGridResponse,
    VariantGridTask,
    VideoKenBurnsRequest,
    VideoResponse,
    VideoStyleRequest,
)
from backend.services.prompt_service import PromptService
from backend.services.storage import StorageService
from backend.services.task_service import TaskService
from backend.services.variant_service import VariantService
from backend.services.video_service import VideoService


router = APIRouter()
storage = StorageService()
prompt_service = PromptService()
task_service = TaskService()
variant_service = VariantService(task_service=task_service)
video_service = VideoService(task_service=task_service)


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    image_id, path = await storage.save_upload(file)
    row = UploadedImage(id=image_id, filename=file.filename or path.name, path=str(path), content_type=file.content_type)
    db.add(row)
    db.commit()
    return UploadResponse(image_id=image_id, filename=row.filename)


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_images(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="At most 20 images can be uploaded at once")

    results: list[UploadResponse] = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"Only image uploads are supported: {file.filename}")
        image_id, path = await storage.save_upload(file)
        row = UploadedImage(id=image_id, filename=file.filename or path.name, path=str(path), content_type=file.content_type)
        db.add(row)
        results.append(UploadResponse(image_id=image_id, filename=row.filename))
    db.commit()
    return BatchUploadResponse(images=results)


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    try:
        task = task_service.create_task(db, image_id=req.image_id, style_id=req.style_id, count=req.count)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GenerateResponse(task_id=task.id, status=task.status)


@router.post("/generate/batch", response_model=BatchGenerateResponse)
def generate_batch(req: BatchGenerateRequest, db: Session = Depends(get_db)):
    tasks: list[BatchGenerateItem] = []
    for image_id in req.image_ids:
        try:
            task = task_service.create_task(db, image_id=image_id, style_id=req.style_id, count=req.count)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=f"{image_id}: {exc}") from exc
        tasks.append(BatchGenerateItem(image_id=image_id, task_id=task.id, status=task.status))
    return BatchGenerateResponse(tasks=tasks)


def _variant_response(payload: dict) -> VariantGridResponse:
    return VariantGridResponse(
        id=payload["id"],
        status=payload["status"],
        image_id=payload["image_id"],
        tasks=[VariantGridTask(**item) for item in payload["tasks"]],
        grid_url=storage.public_url_for_path(payload.get("grid_path")),
        error=payload.get("error"),
    )


@router.post("/generate/variants", response_model=VariantGridResponse)
def generate_variants(req: VariantGridRequest, db: Session = Depends(get_db)):
    try:
        payload = variant_service.create_variant_grid(db, image_id=req.image_id, style_ids=req.style_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _variant_response(payload)


@router.get("/variants/{variant_id}", response_model=VariantGridResponse)
def get_variant_grid(variant_id: str, db: Session = Depends(get_db)):
    payload = variant_service.get_variant_grid(db, variant_id)
    if not payload:
        raise HTTPException(status_code=404, detail="variant grid not found")
    return _variant_response(payload)


def _video_response(payload: dict) -> VideoResponse:
    return VideoResponse(
        id=payload["id"],
        status=payload["status"],
        kind=payload["kind"],
        image_id=payload["image_id"],
        style_id=payload.get("style_id"),
        generation_task_id=payload.get("generation_task_id"),
        video_url=storage.public_url_for_path(payload.get("video_path")),
        error=payload.get("error"),
    )


@router.post("/video/kenburns", response_model=VideoResponse)
def create_kenburns_video(req: VideoKenBurnsRequest, db: Session = Depends(get_db)):
    try:
        payload = video_service.create_kenburns_video(
            db,
            image_id=req.image_id,
            duration=req.duration,
            fps=req.fps,
            width=req.width,
            height=req.height,
            motion=req.motion,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _video_response(payload)


@router.post("/video/style", response_model=VideoResponse)
def create_styled_video(req: VideoStyleRequest, db: Session = Depends(get_db)):
    try:
        payload = video_service.create_styled_video(
            db,
            image_id=req.image_id,
            style_id=req.style_id,
            duration=req.duration,
            fps=req.fps,
            width=req.width,
            height=req.height,
            motion=req.motion,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _video_response(payload)


@router.get("/video/{video_id}", response_model=VideoResponse)
def get_video(video_id: str, db: Session = Depends(get_db)):
    payload = video_service.get_video(db, video_id)
    if not payload:
        raise HTTPException(status_code=404, detail="video not found")
    return _video_response(payload)


@router.get("/task/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskResponse(
        id=task.id,
        status=task.status,
        image_id=task.image_id,
        style_id=task.style_id,
        count=task.count,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        images=[
            TaskImage(
                item_id=item.id,
                seed=item.seed,
                status=item.status,
                url=storage.public_url_for_path(item.output_path),
                error=item.error,
            )
            for item in task.items
        ],
    )


@router.get("/styles", response_model=list[StyleResponse])
def list_styles(db: Session = Depends(get_db)):
    return [StyleResponse.model_validate(style, from_attributes=True) for style in prompt_service.list_styles(db)]
