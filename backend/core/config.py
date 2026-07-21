from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Comfy Flux Platform"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./data/app.db"
    storage_root: Path = Path("./storage")
    workflow_dir: Path = Path("./workflows")

    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_ws_url: str = "ws://127.0.0.1:8188/ws"
    comfyui_mock: bool = False

    generation_max_retries: int = 2
    generation_width: int = 1024
    generation_height: int = 1024
    upscale_factor: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
