#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.request
import uuid


BASE_URL = "http://127.0.0.1:8208"


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"}},
        "2": {"class_type": "EmptyLatentImage", "inputs": {"width": 256, "height": 256, "batch_size": 4}},
        "3": {
            "class_type": "AnimateDiffLoaderV1",
            "inputs": {
                "model": ["1", 0],
                "latents": ["2", 0],
                "model_name": "mm_sd_v15_v2.ckpt",
                "unlimited_area_hack": False,
                "beta_schedule": "sqrt_linear (AnimateDiff)",
            },
        },
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "cute 3D animated character, simple motion"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "low quality, blurry, text, watermark"}},
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 1],
                "seed": 20260727,
                "steps": 4,
                "cfg": 6.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {
            "class_type": "ADE_AnimateDiffCombine",
            "inputs": {
                "images": ["7", 0],
                "frame_rate": 4,
                "loop_count": 0,
                "filename_prefix": "comfy_flux_platform/animatediff/legacy_smoke_test",
                "format": "image/gif",
                "pingpong": False,
                "save_image": True,
            },
        },
    }
    response = post_json("/prompt", {"client_id": str(uuid.uuid4()), "prompt": prompt})
    prompt_id = response["prompt_id"]
    print("prompt_id:", prompt_id)
    for _ in range(180):
        history = get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            print("status:", status)
            print("outputs:", json.dumps(history[prompt_id].get("outputs", {}), ensure_ascii=False)[:2000])
            return 0 if status.get("completed", False) else 1
        time.sleep(2)
    print("timeout waiting for history")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
