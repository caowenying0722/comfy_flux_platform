import json
import shutil
import time
from pathlib import Path
from uuid import uuid4

import requests
import websocket

from backend.core.config import get_settings


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.comfyui_base_url.rstrip("/")
        self.ws_url = self.settings.comfyui_ws_url

    def healthcheck(self) -> bool:
        if self.settings.comfyui_mock:
            return True
        try:
            resp = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return resp.ok
        except requests.RequestException:
            return False

    def upload_image(self, image_path: Path) -> str:
        if self.settings.comfyui_mock:
            return image_path.name
        with image_path.open("rb") as f:
            files = {"image": (image_path.name, f, "application/octet-stream")}
            data = {"overwrite": "true", "type": "input"}
            resp = requests.post(f"{self.base_url}/upload/image", files=files, data=data, timeout=120)
        if not resp.ok:
            raise ComfyUIError(f"ComfyUI upload failed: {resp.status_code} {resp.text}")
        payload = resp.json()
        return payload.get("name") or image_path.name

    def run_workflow(self, workflow: dict, output_path: Path, timeout_seconds: int = 1800) -> Path:
        if self.settings.comfyui_mock:
            source = next((p for p in self.settings.storage_root.glob("original_images/*") if p.is_file()), None)
            if source:
                shutil.copyfile(source, output_path)
            else:
                output_path.write_bytes(b"")
            return output_path

        client_id = str(uuid4())
        prompt_id = self._queue_prompt(workflow, client_id)
        self._wait_until_done(prompt_id, client_id, timeout_seconds)
        outputs = self._collect_output_images(prompt_id)
        if not outputs:
            raise ComfyUIError(f"ComfyUI completed without image outputs, prompt_id={prompt_id}")
        self._download_image(outputs[0], output_path)
        return output_path

    def _queue_prompt(self, workflow: dict, client_id: str) -> str:
        resp = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=60,
        )
        if not resp.ok:
            raise ComfyUIError(f"ComfyUI prompt failed: {resp.status_code} {resp.text}")
        payload = resp.json()
        prompt_id = payload.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError(f"ComfyUI prompt response missing prompt_id: {payload}")
        return prompt_id

    def _wait_until_done(self, prompt_id: str, client_id: str, timeout_seconds: int) -> None:
        deadline = time.time() + timeout_seconds
        ws = websocket.WebSocket()
        ws.connect(f"{self.ws_url}?clientId={client_id}", timeout=10)
        try:
            while time.time() < deadline:
                message = ws.recv()
                if isinstance(message, bytes):
                    continue
                payload = json.loads(message)
                if payload.get("type") == "execution_error":
                    raise ComfyUIError(f"ComfyUI execution error: {payload}")
                if payload.get("type") == "executing":
                    data = payload.get("data", {})
                    if data.get("node") is None and data.get("prompt_id") == prompt_id:
                        return
        finally:
            ws.close()
        raise ComfyUIError(f"ComfyUI execution timed out after {timeout_seconds}s, prompt_id={prompt_id}")

    def _collect_output_images(self, prompt_id: str) -> list[dict]:
        resp = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=60)
        if not resp.ok:
            raise ComfyUIError(f"ComfyUI history failed: {resp.status_code} {resp.text}")
        history = resp.json().get(prompt_id, {})
        images: list[dict] = []
        for node in history.get("outputs", {}).values():
            images.extend(node.get("images", []))
        return images

    def _download_image(self, image: dict, output_path: Path) -> None:
        params = {
            "filename": image["filename"],
            "subfolder": image.get("subfolder", ""),
            "type": image.get("type", "output"),
        }
        resp = requests.get(f"{self.base_url}/view", params=params, timeout=300)
        if not resp.ok:
            raise ComfyUIError(f"ComfyUI view failed: {resp.status_code} {resp.text}")
        output_path.write_bytes(resp.content)
