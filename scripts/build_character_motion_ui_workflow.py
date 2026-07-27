from __future__ import annotations

import json
from pathlib import Path


NEGATIVE = (
    "extra person, missing person, wrong number of people, duplicate person, changed background, new background, different scene, "
    "changed clothing, changed hairstyle, changed face identity, big head turn, extreme pose, cropped person, out of frame, photorealistic, realistic photo, "
    "anime, manga, 2d illustration, text, watermark, logo, low quality, blurry, distorted face, deformed body, bad anatomy, bad hands, extra fingers, missing fingers"
)

FRAMES = [
    ("Frame 1 Neutral", "3D Pixar-style animated character, neutral relaxed expression, eyes open, looking at camera, preserve the same person, preserve hairstyle, clothing, pose, body position, background unchanged, stable composition"),
    ("Frame 2 Smile", "3D Pixar-style animated character, gentle warm smile, eyes open, subtle cheek lift, preserve the same person, preserve hairstyle, clothing, pose, body position, background unchanged, stable composition"),
    ("Frame 3 Blink", "3D Pixar-style animated character, natural blink, eyes gently closed, relaxed face, preserve the same person, preserve hairstyle, clothing, pose, body position, background unchanged, stable composition"),
    ("Frame 4 Slight Look", "3D Pixar-style animated character, eyes looking slightly to the side, very subtle head angle, small lively expression, preserve the same person, preserve hairstyle, clothing, pose, body position, background unchanged, stable composition"),
]


nodes: list[dict] = []
links: list[list] = []
next_link_id = 1


def add_link(origin_id: int, origin_slot: int, target_id: int, target_slot: int, typ: str) -> int:
    global next_link_id
    link_id = next_link_id
    next_link_id += 1
    links.append([link_id, origin_id, origin_slot, target_id, target_slot, typ])
    return link_id


def inp(name: str, typ: str, link: int) -> dict:
    return {"name": name, "type": typ, "link": link}


def out(name: str, typ: str, links_: list[int] | None, slot: int) -> dict:
    return {"name": name, "type": typ, "links": links_, "slot_index": slot}


def node(node_id: int, typ: str, pos: list[int], size: list[int], inputs: list[dict], outputs: list[dict], widgets: list, title: str | None = None) -> dict:
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


load_to_scale = add_link(2, 0, 3, 0, "IMAGE")
scale_to_canny = add_link(3, 0, 4, 0, "IMAGE")
scale_to_preview = add_link(3, 0, 5, 0, "IMAGE")
canny_to_preview = add_link(4, 0, 6, 0, "IMAGE")

nodes.extend(
    [
        node(
            1,
            "CheckpointLoaderSimple",
            [40, 80],
            [340, 98],
            [],
            [out("MODEL", "MODEL", None, 0), out("CLIP", "CLIP", None, 1), out("VAE", "VAE", None, 2)],
            ["DreamShaperXL_Lightning.safetensors"],
        ),
        node(
            2,
            "LoadImage",
            [40, 250],
            [340, 314],
            [],
            [out("IMAGE", "IMAGE", [load_to_scale], 0), out("MASK", "MASK", None, 1)],
            ["example.png", "image"],
        ),
        node(
            3,
            "ImageScale",
            [430, 290],
            [315, 130],
            [inp("image", "IMAGE", load_to_scale)],
            [out("IMAGE", "IMAGE", [scale_to_canny, scale_to_preview], 0)],
            ["lanczos", 768, 512, "center"],
        ),
        node(4, "Canny", [805, 430], [315, 106], [inp("image", "IMAGE", scale_to_canny)], [out("IMAGE", "IMAGE", [canny_to_preview], 0)], [0.25, 0.75]),
    ]
)

nodes.extend(
    [
        node(5, "PreviewImage", [805, 160], [300, 220], [inp("images", "IMAGE", scale_to_preview)], [], [], "Input Preview"),
        node(6, "PreviewImage", [1170, 420], [300, 220], [inp("images", "IMAGE", canny_to_preview)], [], [], "Canny Preview"),
        node(7, "ControlNetLoader", [805, 700], [360, 58], [], [out("CONTROL_NET", "CONTROL_NET", None, 0)], ["controlnet-canny-sdxl-1.0-small.safetensors"]),
    ]
)

gif_inputs = []
base_id = 10
for i, (title, prompt) in enumerate(FRAMES):
    y = 40 + i * 420
    pos_id = base_id + i * 8
    neg_id = pos_id + 1
    apply_id = pos_id + 2
    encode_id = pos_id + 3
    sampler_id = pos_id + 4
    decode_id = pos_id + 5
    preview_id = pos_id + 6
    save_id = pos_id + 7

    clip_pos = add_link(1, 1, pos_id, 0, "CLIP")
    clip_neg = add_link(1, 1, neg_id, 0, "CLIP")
    pos_apply = add_link(pos_id, 0, apply_id, 0, "CONDITIONING")
    neg_apply = add_link(neg_id, 0, apply_id, 1, "CONDITIONING")
    control_apply = add_link(7, 0, apply_id, 2, "CONTROL_NET")
    canny_apply = add_link(4, 0, apply_id, 3, "IMAGE")
    scale_encode = add_link(3, 0, encode_id, 0, "IMAGE")
    vae_encode = add_link(1, 2, encode_id, 1, "VAE")
    model_sampler = add_link(1, 0, sampler_id, 0, "MODEL")
    pos_sampler = add_link(apply_id, 0, sampler_id, 1, "CONDITIONING")
    neg_sampler = add_link(apply_id, 1, sampler_id, 2, "CONDITIONING")
    latent_sampler = add_link(encode_id, 0, sampler_id, 3, "LATENT")
    sampler_decode = add_link(sampler_id, 0, decode_id, 0, "LATENT")
    vae_decode = add_link(1, 2, decode_id, 1, "VAE")
    decode_preview = add_link(decode_id, 0, preview_id, 0, "IMAGE")
    decode_save = add_link(decode_id, 0, save_id, 0, "IMAGE")
    decode_gif = add_link(decode_id, 0, 100, i, "IMAGE")
    gif_inputs.append(inp(f"image_{i + 1}", "IMAGE", decode_gif))

    nodes.extend(
        [
            node(pos_id, "CLIPTextEncode", [1530, y], [470, 170], [inp("clip", "CLIP", clip_pos)], [out("CONDITIONING", "CONDITIONING", [pos_apply], 0)], [prompt], f"{title} Positive"),
            node(neg_id, "CLIPTextEncode", [1530, y + 185], [470, 145], [inp("clip", "CLIP", clip_neg)], [out("CONDITIONING", "CONDITIONING", [neg_apply], 0)], [NEGATIVE], f"{title} Negative"),
            node(
                apply_id,
                "ControlNetApplyAdvanced",
                [2040, y + 80],
                [330, 186],
                [inp("positive", "CONDITIONING", pos_apply), inp("negative", "CONDITIONING", neg_apply), inp("control_net", "CONTROL_NET", control_apply), inp("image", "IMAGE", canny_apply)],
                [out("positive", "CONDITIONING", [pos_sampler], 0), out("negative", "CONDITIONING", [neg_sampler], 1)],
                [0.9, 0.0, 0.9],
                f"{title} ControlNet",
            ),
            node(encode_id, "VAEEncode", [2040, y + 290], [210, 46], [inp("pixels", "IMAGE", scale_encode), inp("vae", "VAE", vae_encode)], [out("LATENT", "LATENT", [latent_sampler], 0)], [], f"{title} VAEEncode"),
            node(
                sampler_id,
                "KSampler",
                [2420, y + 80],
                [315, 262],
                [inp("model", "MODEL", model_sampler), inp("positive", "CONDITIONING", pos_sampler), inp("negative", "CONDITIONING", neg_sampler), inp("latent_image", "LATENT", latent_sampler)],
                [out("LATENT", "LATENT", [sampler_decode], 0)],
                [300000 + i, "fixed", 8, 2.0, "dpmpp_sde", "karras", 0.38],
                f"{title} Sampler",
            ),
            node(decode_id, "VAEDecode", [2780, y + 140], [210, 46], [inp("samples", "LATENT", sampler_decode), inp("vae", "VAE", vae_decode)], [out("IMAGE", "IMAGE", [decode_preview, decode_save, decode_gif], 0)], [], f"{title} Decode"),
            node(preview_id, "PreviewImage", [3030, y + 60], [300, 220], [inp("images", "IMAGE", decode_preview)], [], [], f"{title} Preview"),
            node(save_id, "SaveImage", [3030, y + 285], [300, 120], [inp("images", "IMAGE", decode_save)], [], [f"comfy_flux_platform/character_motion/{i + 1}_{title.lower().replace(' ', '_')}"], f"{title} Save"),
        ]
    )

nodes.append(
    node(
        100,
        "ImageSequenceGIF",
        [3430, 540],
        [390, 260],
        gif_inputs,
        [],
        ["comfy_flux_platform/video_ui/character_motion", 500, True, 768, 512],
        "Image Sequence GIF",
    )
)

# Rebuild output link lists.
links_by_origin: dict[tuple[int, int], list[int]] = {}
for link in links:
    links_by_origin.setdefault((link[1], link[2]), []).append(link[0])
for item in nodes:
    for output in item.get("outputs", []):
        output["links"] = links_by_origin.get((item["id"], output.get("slot_index", 0))) or None

workflow = {
    "last_node_id": 100,
    "last_link_id": next_link_id - 1,
    "nodes": nodes,
    "links": links,
    "groups": [
        {"title": "Shared input / Canny ControlNet", "bounding": [20, 40, 1450, 760], "color": "#3f789e", "font_size": 24},
        {"title": "Low-denoise keyframes", "bounding": [1500, 20, 1840, 1700], "color": "#8a6fb0", "font_size": 24},
        {"title": "GIF export", "bounding": [3400, 500, 460, 360], "color": "#2d8f6f", "font_size": 24},
    ],
    "config": {},
    "extra": {"ds": {"scale": 0.45, "offset": [20, 20]}},
    "version": 0.4,
}

target = Path(__file__).resolve().parents[1] / "workflows" / "pixar_character_motion_ui.json"
target.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
print(target)
