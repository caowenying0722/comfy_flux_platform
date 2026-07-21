from backend.core.config import get_settings
from backend.database.session import Base, SessionLocal, engine
from backend.services.prompt_service import PromptService


def main() -> None:
    settings = get_settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.workflow_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite:///")
        if db_path != ":memory:":
            from pathlib import Path

            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        PromptService().seed_defaults(db)
    print("database initialized")


if __name__ == "__main__":
    main()
