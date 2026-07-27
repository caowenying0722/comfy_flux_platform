#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.request
import uuid


BASE_URL = "http://127.0.0.1:8208"


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    client_id = str(uuid.uuid4())
    prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"},
        },
        "2": {
            "class_type": "ADE_AnimateDiffLoaderGen1",
            "inputs": {
                "model": ["1", 0],
                "model_name": "mm_sd_v15_v2.ckpt",
                "beta_schedule": "autoselect",
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": "3D Pixar style animated character, gentle natural movement, high quality animation",
            },
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": "low quality, blurry, flicker, distorted face, bad anatomy, text, watermark",
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 384, "height": 384, "batch_size": 8},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": 20260727,
                "steps": 8,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "ADE_AnimateDiffCombine",
            "inputs": {
                "images": ["7", 0],
                "frame_rate": 8,
                "loop_count": 0,
                "filename_prefix": "comfy_flux_platform/animatediff/smoke_test",
                "format": "image/gif",
                "pingpong": False,
                "save_image": True,
            },
        },
    }

    response = post_json("/prompt", {"client_id": client_id, "prompt": prompt})
    prompt_id = response["prompt_id"]
    print("prompt_id:", prompt_id)

    for _ in range(240):
        history = get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})
            print("status:", status)
            outputs = entry.get("outputs", {})
            print("outputs:", json.dumps(outputs, ensure_ascii=False)[:2000])
            completed = status.get("completed", False)
            return 0 if completed else 1
        time.sleep(2)

    print("timeout waiting for history")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
