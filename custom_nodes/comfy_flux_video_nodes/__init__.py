import math
from pathlib import Path

import folder_paths
import numpy as np
import torch
from PIL import Image, ImageDraw


class KenBurnsGIF:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "comfy_flux_platform/video_ui/kenburns"}),
                "duration": ("FLOAT", {"default": 4.0, "min": 1.0, "max": 15.0, "step": 0.5}),
                "fps": ("INT", {"default": 12, "min": 8, "max": 24, "step": 1}),
                "width": ("INT", {"default": 1152, "min": 256, "max": 1920, "step": 16}),
                "height": ("INT", {"default": 768, "min": 256, "max": 1080, "step": 16}),
                "motion": (["slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"],),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "Comfy Flux Platform/video"

    def save(self, images, filename_prefix, duration, fps, width, height, motion):
        output_dir = Path(folder_paths.get_output_directory())
        subfolder = Path(filename_prefix).parent.as_posix()
        prefix = Path(filename_prefix).name
        target_dir = output_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        counter = 1
        while True:
            filename = f"{prefix}_{counter:05}.gif"
            output_path = target_dir / filename
            if not output_path.exists():
                break
            counter += 1

        image_tensor = images[0]
        source = self._tensor_to_pil(image_tensor)
        frame_count = max(2, int(duration * fps))
        frames = [self._frame(source, i, frame_count, width, height, motion) for i in range(frame_count)]
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0,
            optimize=True,
        )

        return {
            "ui": {
                "images": [
                    {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ]
            }
        }

    def _tensor_to_pil(self, image_tensor: torch.Tensor) -> Image.Image:
        array = image_tensor.detach().cpu().numpy()
        array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(array).convert("RGB")

    def _frame(self, source: Image.Image, index: int, frame_count: int, width: int, height: int, motion: str) -> Image.Image:
        progress = index / max(1, frame_count - 1)
        eased = 0.5 - 0.5 * math.cos(progress * math.pi)

        base = self._cover(source, width, height)
        zoom = 1.0 + 0.08 * eased
        if motion == "slow_zoom_out":
            zoom = 1.08 - 0.08 * eased
        elif motion in {"pan_left", "pan_right"}:
            zoom = 1.06

        zoom_w = int(width * zoom)
        zoom_h = int(height * zoom)
        enlarged = base.resize((zoom_w, zoom_h), Image.Resampling.LANCZOS)

        max_x = max(0, zoom_w - width)
        max_y = max(0, zoom_h - height)
        if motion == "pan_left":
            left = int(max_x * (1 - eased))
            top = max_y // 2
        elif motion == "pan_right":
            left = int(max_x * eased)
            top = max_y // 2
        else:
            left = max_x // 2
            top = max_y // 2

        frame = enlarged.crop((left, top, left + width, top + height))
        return self._add_subtle_vignette(frame)

    def _cover(self, source: Image.Image, width: int, height: int) -> Image.Image:
        src_w, src_h = source.size
        scale = max(width / src_w, height / src_h)
        resized = source.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - width) // 2
        top = (resized.height - height) // 2
        return resized.crop((left, top, left + width, top + height))

    def _add_subtle_vignette(self, frame: Image.Image) -> Image.Image:
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = frame.size
        for i in range(24):
            alpha = int(i * 1.6)
            draw.rectangle((i, i, w - i - 1, h - i - 1), outline=(0, 0, 0, alpha))
        return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


class ImageSequenceGIF:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "comfy_flux_platform/video_ui/character_motion"}),
                "frame_duration_ms": ("INT", {"default": 500, "min": 120, "max": 2000, "step": 20}),
                "ping_pong": ("BOOLEAN", {"default": True}),
                "width": ("INT", {"default": 768, "min": 256, "max": 1920, "step": 16}),
                "height": ("INT", {"default": 512, "min": 256, "max": 1080, "step": 16}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "Comfy Flux Platform/video"

    def save(self, image_1, image_2, image_3, image_4, filename_prefix, frame_duration_ms, ping_pong, width, height):
        output_dir = Path(folder_paths.get_output_directory())
        subfolder = Path(filename_prefix).parent.as_posix()
        prefix = Path(filename_prefix).name
        target_dir = output_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        counter = 1
        while True:
            filename = f"{prefix}_{counter:05}.gif"
            output_path = target_dir / filename
            if not output_path.exists():
                break
            counter += 1

        frames = [
            self._cover(self._tensor_to_pil(image_1[0]), width, height),
            self._cover(self._tensor_to_pil(image_2[0]), width, height),
            self._cover(self._tensor_to_pil(image_3[0]), width, height),
            self._cover(self._tensor_to_pil(image_4[0]), width, height),
        ]
        if ping_pong:
            frames = frames + frames[-2:0:-1]

        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0,
            optimize=True,
        )

        return {
            "ui": {
                "images": [
                    {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ]
            }
        }

    def _tensor_to_pil(self, image_tensor: torch.Tensor) -> Image.Image:
        array = image_tensor.detach().cpu().numpy()
        array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(array).convert("RGB")

    def _cover(self, source: Image.Image, width: int, height: int) -> Image.Image:
        src_w, src_h = source.size
        scale = max(width / src_w, height / src_h)
        resized = source.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - width) // 2
        top = (resized.height - height) // 2
        return resized.crop((left, top, left + width, top + height))


NODE_CLASS_MAPPINGS = {
    "KenBurnsGIF": KenBurnsGIF,
    "ImageSequenceGIF": ImageSequenceGIF,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KenBurnsGIF": "Ken Burns GIF",
    "ImageSequenceGIF": "Image Sequence GIF",
}
