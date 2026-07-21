from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.entities import GenerationTask, UploadedImage
from backend.schemas import GenerateRequest, GenerateResponse, StyleResponse, TaskImage, TaskResponse, UploadResponse
from backend.services.prompt_service import PromptService
from backend.services.storage import StorageService
from backend.services.task_service import TaskService


router = APIRouter()
storage = StorageService()
prompt_service = PromptService()
task_service = TaskService()


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    image_id, path = await storage.save_upload(file)
    row = UploadedImage(id=image_id, filename=file.filename or path.name, path=str(path), content_type=file.content_type)
    db.add(row)
    db.commit()
    return UploadResponse(image_id=image_id, filename=row.filename)


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    try:
        task = task_service.create_task(db, image_id=req.image_id, style_id=req.style_id, count=req.count)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GenerateResponse(task_id=task.id, status=task.status)


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
