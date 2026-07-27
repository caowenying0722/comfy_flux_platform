from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = PROJECT_ROOT / "workflows"

POSITIVE = (
    "3D Pixar style animated character video, lively expressive character, "
    "gentle natural head movement, subtle body motion, charming animated movie look, "
    "large friendly eyes, rounded face, soft cinematic lighting, colorful high quality 3D animation"
)

NEGATIVE = (
    "low quality, blurry, flicker, jitter, distorted face, deformed body, bad anatomy, bad hands, "
    "extra fingers, missing fingers, extra person, duplicate person, wrong number of people, "
    "text, watermark, logo, cropped, out of frame, harsh lighting"
)


def out(name: str, typ: str, links: list[int] | None, slot: int) -> dict:
    return {"name": name, "type": typ, "links": links, "slot_index": slot}


def inp(name: str, typ: str, link: int) -> dict:
    return {"name": name, "type": typ, "link": link}


def make_builder():
    links: list[list] = []
    next_link_id = 1

    def add_link(origin_id: int, origin_slot: int, target_id: int, target_slot: int, typ: str) -> int:
        nonlocal next_link_id
        link_id = next_link_id
        next_link_id += 1
        links.append([link_id, origin_id, origin_slot, target_id, target_slot, typ])
        return link_id

    def node(
        node_id: int,
        typ: str,
        pos: list[int],
        size: list[int],
        inputs: list[dict],
        outputs: list[dict],
        widgets: list,
        title: str | None = None,
    ) -> dict:
        data = {
            "id": node_id,
            "type": typ,
            "pos": pos,
            "size": size,
            "flags": {},
            "order": node_id,
            "mode": 0,
            "inputs": inputs,
            "outputs": outputs,
            "properties": {"Node name for S&R": typ},
            "widgets_values": widgets,
        }
        if title:
            data["title"] = title
        return data

    return links, add_link, node


def workflow_base(nodes: list[dict], links: list[list], groups: list[dict]) -> dict:
    return {
        "last_node_id": max(node["id"] for node in nodes),
        "last_link_id": max((link[0] for link in links), default=0),
        "nodes": nodes,
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {"ds": {"scale": 0.75, "offset": [80, 40]}},
        "version": 0.4,
    }


def build_txt2video() -> dict:
    links, add_link, node = make_builder()
    nodes: list[dict] = []

    ckpt_to_ad = add_link(1, 0, 2, 0, "MODEL")
    ad_to_sampler = add_link(2, 0, 6, 0, "MODEL")
    clip_to_pos = add_link(1, 1, 3, 0, "CLIP")
    clip_to_neg = add_link(1, 1, 4, 0, "CLIP")
    pos_to_sampler = add_link(3, 0, 6, 1, "CONDITIONING")
    neg_to_sampler = add_link(4, 0, 6, 2, "CONDITIONING")
    latent_to_sampler = add_link(5, 0, 6, 3, "LATENT")
    sampler_to_decode = add_link(6, 0, 7, 0, "LATENT")
    vae_to_decode = add_link(1, 2, 7, 1, "VAE")
    decode_to_preview = add_link(7, 0, 8, 0, "IMAGE")
    decode_to_combine = add_link(7, 0, 9, 0, "IMAGE")

    nodes.extend(
        [
            node(
                1,
                "CheckpointLoaderSimple",
                [40, 80],
                [340, 98],
                [],
                [
                    out("MODEL", "MODEL", [ckpt_to_ad], 0),
                    out("CLIP", "CLIP", [clip_to_pos, clip_to_neg], 1),
                    out("VAE", "VAE", [vae_to_decode], 2),
                ],
                ["v1-5-pruned-emaonly-fp16.safetensors"],
                "SD1.5 Checkpoint",
            ),
            node(
                2,
                "ADE_AnimateDiffLoaderGen1",
                [430, 80],
                [360, 86],
                [inp("model", "MODEL", ckpt_to_ad)],
                [out("MODEL", "MODEL", [ad_to_sampler], 0)],
                ["mm_sd_v15_v2.ckpt", "autoselect"],
                "AnimateDiff Motion Model",
            ),
            node(3, "CLIPTextEncode", [40, 240], [420, 180], [inp("clip", "CLIP", clip_to_pos)], [out("CONDITIONING", "CONDITIONING", [pos_to_sampler], 0)], [POSITIVE], "Positive Prompt"),
            node(4, "CLIPTextEncode", [40, 460], [420, 180], [inp("clip", "CLIP", clip_to_neg)], [out("CONDITIONING", "CONDITIONING", [neg_to_sampler], 0)], [NEGATIVE], "Negative Prompt"),
            node(5, "EmptyLatentImage", [500, 250], [300, 106], [], [out("LATENT", "LATENT", [latent_to_sampler], 0)], [512, 512, 16], "16 Frames Latent"),
            node(
                6,
                "KSampler",
                [850, 170],
                [315, 262],
                [
                    inp("model", "MODEL", ad_to_sampler),
                    inp("positive", "CONDITIONING", pos_to_sampler),
                    inp("negative", "CONDITIONING", neg_to_sampler),
                    inp("latent_image", "LATENT", latent_to_sampler),
                ],
                [out("LATENT", "LATENT", [sampler_to_decode], 0)],
                [20260727, "randomize", 20, 7.0, "euler", "normal", 1.0],
                "Video Sampler",
            ),
            node(7, "VAEDecode", [1210, 210], [210, 46], [inp("samples", "LATENT", sampler_to_decode), inp("vae", "VAE", vae_to_decode)], [out("IMAGE", "IMAGE", [decode_to_preview, decode_to_combine], 0)], [], "Decode Frames"),
            node(8, "PreviewImage", [1470, 70], [320, 240], [inp("images", "IMAGE", decode_to_preview)], [], [], "Preview Frames"),
            node(
                9,
                "ADE_AnimateDiffCombine",
                [1470, 380],
                [360, 174],
                [inp("images", "IMAGE", decode_to_combine)],
                [out("GIF", "GIF", None, 0)],
                [8, 0, "comfy_flux_platform/animatediff/txt2video", "image/gif", False, True],
                "Save GIF",
            ),
        ]
    )

    return workflow_base(nodes, links, [{"title": "AnimateDiff SD1.5 Txt2Video", "bounding": [20, 40, 1840, 560], "color": "#3f789e", "font_size": 24}])


def build_img2video() -> dict:
    links, add_link, node = make_builder()
    nodes: list[dict] = []

    ckpt_to_ad = add_link(1, 0, 2, 0, "MODEL")
    ad_to_sampler = add_link(2, 0, 9, 0, "MODEL")
    clip_to_pos = add_link(1, 1, 3, 0, "CLIP")
    clip_to_neg = add_link(1, 1, 4, 0, "CLIP")
    pos_to_sampler = add_link(3, 0, 9, 1, "CONDITIONING")
    neg_to_sampler = add_link(4, 0, 9, 2, "CONDITIONING")
    image_to_scale = add_link(5, 0, 6, 0, "IMAGE")
    scale_to_preview = add_link(6, 0, 7, 0, "IMAGE")
    scale_to_encode = add_link(6, 0, 8, 0, "IMAGE")
    vae_to_encode = add_link(1, 2, 8, 1, "VAE")
    encode_to_repeat = add_link(8, 0, 10, 0, "LATENT")
    repeat_to_sampler = add_link(10, 0, 9, 3, "LATENT")
    sampler_to_decode = add_link(9, 0, 11, 0, "LATENT")
    vae_to_decode = add_link(1, 2, 11, 1, "VAE")
    decode_to_preview = add_link(11, 0, 12, 0, "IMAGE")
    decode_to_combine = add_link(11, 0, 13, 0, "IMAGE")

    nodes.extend(
        [
            node(
                1,
                "CheckpointLoaderSimple",
                [40, 80],
                [340, 98],
                [],
                [
                    out("MODEL", "MODEL", [ckpt_to_ad], 0),
                    out("CLIP", "CLIP", [clip_to_pos, clip_to_neg], 1),
                    out("VAE", "VAE", [vae_to_encode, vae_to_decode], 2),
                ],
                ["v1-5-pruned-emaonly-fp16.safetensors"],
                "SD1.5 Checkpoint",
            ),
            node(
                2,
                "ADE_AnimateDiffLoaderGen1",
                [430, 80],
                [360, 86],
                [inp("model", "MODEL", ckpt_to_ad)],
                [out("MODEL", "MODEL", [ad_to_sampler], 0)],
                ["mm_sd_v15_v2.ckpt", "autoselect"],
                "AnimateDiff Motion Model",
            ),
            node(3, "CLIPTextEncode", [40, 240], [420, 180], [inp("clip", "CLIP", clip_to_pos)], [out("CONDITIONING", "CONDITIONING", [pos_to_sampler], 0)], [POSITIVE + ", preserve the same main character and composition"], "Positive Prompt"),
            node(4, "CLIPTextEncode", [40, 460], [420, 180], [inp("clip", "CLIP", clip_to_neg)], [out("CONDITIONING", "CONDITIONING", [neg_to_sampler], 0)], [NEGATIVE + ", changed identity, changed background"], "Negative Prompt"),
            node(5, "LoadImage", [500, 230], [315, 314], [], [out("IMAGE", "IMAGE", [image_to_scale], 0), out("MASK", "MASK", None, 1)], ["example.png", "image"], "Upload Source Image"),
            node(6, "ImageScale", [870, 260], [315, 130], [inp("image", "IMAGE", image_to_scale)], [out("IMAGE", "IMAGE", [scale_to_preview, scale_to_encode], 0)], ["lanczos", 512, 512, "center"], "Scale to 512"),
            node(7, "PreviewImage", [1230, 70], [300, 220], [inp("images", "IMAGE", scale_to_preview)], [], [], "Input Preview"),
            node(8, "VAEEncode", [1230, 340], [210, 46], [inp("pixels", "IMAGE", scale_to_encode), inp("vae", "VAE", vae_to_encode)], [out("LATENT", "LATENT", [encode_to_repeat], 0)], [], "Encode Source"),
            node(10, "RepeatLatentBatch", [1490, 340], [260, 58], [inp("samples", "LATENT", encode_to_repeat)], [out("LATENT", "LATENT", [repeat_to_sampler], 0)], [16], "Repeat to 16 Frames"),
            node(
                9,
                "KSampler",
                [1800, 170],
                [315, 262],
                [
                    inp("model", "MODEL", ad_to_sampler),
                    inp("positive", "CONDITIONING", pos_to_sampler),
                    inp("negative", "CONDITIONING", neg_to_sampler),
                    inp("latent_image", "LATENT", repeat_to_sampler),
                ],
                [out("LATENT", "LATENT", [sampler_to_decode], 0)],
                [20260727, "randomize", 20, 7.0, "euler", "normal", 0.62],
                "Video Sampler",
            ),
            node(11, "VAEDecode", [2160, 210], [210, 46], [inp("samples", "LATENT", sampler_to_decode), inp("vae", "VAE", vae_to_decode)], [out("IMAGE", "IMAGE", [decode_to_preview, decode_to_combine], 0)], [], "Decode Frames"),
            node(12, "PreviewImage", [2420, 70], [320, 240], [inp("images", "IMAGE", decode_to_preview)], [], [], "Preview Frames"),
            node(
                13,
                "ADE_AnimateDiffCombine",
                [2420, 380],
                [360, 174],
                [inp("images", "IMAGE", decode_to_combine)],
                [out("GIF", "GIF", None, 0)],
                [8, 0, "comfy_flux_platform/animatediff/img2video", "image/gif", False, True],
                "Save GIF",
            ),
        ]
    )

    return workflow_base(nodes, links, [{"title": "AnimateDiff SD1.5 Img2Video", "bounding": [20, 40, 2800, 560], "color": "#6b5b95", "font_size": 24}])


def main() -> None:
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "animatediff_sd15_txt2video_ui.json": build_txt2video(),
        "animatediff_sd15_img2video_ui.json": build_img2video(),
    }
    for name, workflow in outputs.items():
        path = WORKFLOW_DIR / name
        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
