from __future__ import annotations

import json
from pathlib import Path


POSITIVE_PROMPTS = [
    (
        "Pixar ControlNet",
        "3D Pixar-style animated movie still, stylized 3D cartoon character, cute and expressive face, large friendly eyes, rounded facial features, soft smooth materials, warm cinematic lighting, colorful but natural, high quality 3D animation render, preserve the same person or people, preserve the correct number of people, preserve hairstyle, clothing, pose and body position, keep the original background unchanged, keep the original composition, horizontal 3:2 image",
        0.58,
        0.75,
    ),
    (
        "DreamShaper Pixar",
        "3D Pixar-style character rendering, stylized 3D animated movie look, cute expressive character, rounded face, large friendly eyes, smooth materials, soft warm lighting, colorful 3D cartoon render, preserve the same person or people, preserve the correct number of people, keep original composition and background structure",
        0.66,
        0.55,
    ),
    (
        "Anime Comic",
        "lively anime comic illustration, expressive eyes, clean line art, vibrant colors, soft cel shading, charming character design, energetic atmosphere, polished manga cover style, preserve the same person or people and original composition",
        0.62,
        0.65,
    ),
    (
        "3D Figurine",
        "3D collectible figurine, premium blind box toy style, cute chibi proportions, smooth resin material, miniature diorama feeling, studio lighting, detailed sculpt, preserve the same person or people and background structure",
        0.64,
        0.65,
    ),
    (
        "Guofeng Art",
        "traditional Chinese guofeng illustration, elegant ink wash aesthetics, soft silk texture, refined composition, poetic atmosphere, stylized character portrait, preserve the same person or people and original layout",
        0.60,
        0.70,
    ),
    (
        "Oil Painting",
        "oil painting portrait, rich brush strokes, detailed canvas texture, classical composition, museum quality, dramatic but soft lighting, preserve the same person or people and original composition",
        0.58,
        0.75,
    ),
]

NEGATIVE_PROMPT = (
    "extra person, missing person, wrong number of people, duplicate person, changed background, new background, different scene, "
    "added objects, removed objects, changed clothing, changed pose, changed hairstyle, changed face identity, cropped person, out of frame, "
    "photorealistic if not requested, realistic photo if not requested, text, watermark, logo, low quality, blurry, distorted face, deformed body, "
    "bad anatomy, bad hands, extra fingers, missing fingers"
)


def out(name: str, typ: str, links: list[int] | None, slot: int) -> dict:
    return {"name": name, "type": typ, "links": links, "slot_index": slot}


def inp(name: str, typ: str, link: int) -> dict:
    return {"name": name, "type": typ, "link": link}


nodes: list[dict] = []
links: list[list] = []
next_link_id = 1


def add_link(origin_id: int, origin_slot: int, target_id: int, target_slot: int, typ: str) -> int:
    global next_link_id
    link_id = next_link_id
    next_link_id += 1
    links.append([link_id, origin_id, origin_slot, target_id, target_slot, typ])
    return link_id


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


# Shared nodes.
model_to_samplers: list[int] = []
clip_to_positive: list[int] = []
clip_to_negative: list[int] = []
vae_to_encodes: list[int] = []
vae_to_decodes: list[int] = []
scaled_to_canny = add_link(3, 0, 4, 0, "IMAGE")
scaled_to_preview = add_link(3, 0, 6, 0, "IMAGE")
canny_to_control_applies: list[int] = []
control_to_applies: list[int] = []
scaled_to_encodes: list[int] = []
decoded_to_batch_or_save: list[int] = []

nodes.append(
    node(
        1,
        "CheckpointLoaderSimple",
        [40, 80],
        [340, 98],
        [],
        [
            out("MODEL", "MODEL", model_to_samplers, 0),
            out("CLIP", "CLIP", clip_to_positive + clip_to_negative, 1),
            out("VAE", "VAE", vae_to_encodes + vae_to_decodes, 2),
        ],
        ["DreamShaperXL_Lightning.safetensors"],
    )
)
nodes.append(
    node(
        2,
        "LoadImage",
        [40, 250],
        [340, 314],
        [],
        [out("IMAGE", "IMAGE", [add_link(2, 0, 3, 0, "IMAGE")], 0), out("MASK", "MASK", None, 1)],
        ["example.png", "image"],
    )
)
nodes.append(
    node(
        3,
        "ImageScale",
        [430, 300],
        [315, 130],
        [inp("image", "IMAGE", 3)],
        [out("IMAGE", "IMAGE", [scaled_to_canny, scaled_to_preview] + scaled_to_encodes, 0)],
        ["lanczos", 1152, 768, "center"],
    )
)
nodes.append(
    node(
        4,
        "Canny",
        [805, 430],
        [315, 106],
        [inp("image", "IMAGE", scaled_to_canny)],
        [out("IMAGE", "IMAGE", canny_to_control_applies + [add_link(4, 0, 5, 0, "IMAGE")], 0)],
        [0.25, 0.75],
    )
)
nodes.append(
    node(
        5,
        "PreviewImage",
        [1170, 420],
        [300, 240],
        [inp("images", "IMAGE", 4)],
        [],
        [],
        "Canny Preview",
    )
)
nodes.append(
    node(
        6,
        "PreviewImage",
        [805, 170],
        [300, 220],
        [inp("images", "IMAGE", scaled_to_preview)],
        [],
        [],
        "Input Preview",
    )
)
nodes.append(
    node(
        7,
        "ControlNetLoader",
        [805, 700],
        [360, 58],
        [],
        [out("CONTROL_NET", "CONTROL_NET", control_to_applies, 0)],
        ["controlnet-canny-sdxl-1.0-small.safetensors"],
    )
)

decoded_image_links: list[int] = []
branch_start = 10
for i, (label, positive_prompt, denoise, strength) in enumerate(POSITIVE_PROMPTS):
    y = 40 + i * 360
    positive_id = branch_start + i * 7
    negative_id = positive_id + 1
    apply_id = positive_id + 2
    encode_id = positive_id + 3
    sampler_id = positive_id + 4
    decode_id = positive_id + 5
    preview_id = positive_id + 6

    clip_pos = add_link(1, 1, positive_id, 0, "CLIP")
    clip_neg = add_link(1, 1, negative_id, 0, "CLIP")
    positive_to_apply = add_link(positive_id, 0, apply_id, 0, "CONDITIONING")
    negative_to_apply = add_link(negative_id, 0, apply_id, 1, "CONDITIONING")
    canny_to_apply = add_link(4, 0, apply_id, 3, "IMAGE")
    control_to_apply = add_link(7, 0, apply_id, 2, "CONTROL_NET")
    scaled_to_encode = add_link(3, 0, encode_id, 0, "IMAGE")
    vae_to_encode = add_link(1, 2, encode_id, 1, "VAE")
    apply_to_sampler_pos = add_link(apply_id, 0, sampler_id, 1, "CONDITIONING")
    apply_to_sampler_neg = add_link(apply_id, 1, sampler_id, 2, "CONDITIONING")
    model_to_sampler = add_link(1, 0, sampler_id, 0, "MODEL")
    latent_to_sampler = add_link(encode_id, 0, sampler_id, 3, "LATENT")
    sampler_to_decode = add_link(sampler_id, 0, decode_id, 0, "LATENT")
    vae_to_decode = add_link(1, 2, decode_id, 1, "VAE")
    decode_to_preview = add_link(decode_id, 0, preview_id, 0, "IMAGE")

    model_to_samplers.append(model_to_sampler)
    clip_to_positive.append(clip_pos)
    clip_to_negative.append(clip_neg)
    vae_to_encodes.append(vae_to_encode)
    vae_to_decodes.append(vae_to_decode)
    canny_to_control_applies.append(canny_to_apply)
    control_to_applies.append(control_to_apply)
    scaled_to_encodes.append(scaled_to_encode)
    decoded_image_links.append(decode_to_preview)

    nodes.extend(
        [
            node(positive_id, "CLIPTextEncode", [1530, y], [470, 170], [inp("clip", "CLIP", clip_pos)], [out("CONDITIONING", "CONDITIONING", [positive_to_apply], 0)], [positive_prompt], f"{label} Positive"),
            node(negative_id, "CLIPTextEncode", [1530, y + 185], [470, 145], [inp("clip", "CLIP", clip_neg)], [out("CONDITIONING", "CONDITIONING", [negative_to_apply], 0)], [NEGATIVE_PROMPT], f"{label} Negative"),
            node(
                apply_id,
                "ControlNetApplyAdvanced",
                [2040, y + 80],
                [330, 186],
                [
                    inp("positive", "CONDITIONING", positive_to_apply),
                    inp("negative", "CONDITIONING", negative_to_apply),
                    inp("control_net", "CONTROL_NET", control_to_apply),
                    inp("image", "IMAGE", canny_to_apply),
                ],
                [out("positive", "CONDITIONING", [apply_to_sampler_pos], 0), out("negative", "CONDITIONING", [apply_to_sampler_neg], 1)],
                [strength, 0.0, 0.8],
                f"{label} ControlNet",
            ),
            node(encode_id, "VAEEncode", [2040, y + 290], [210, 46], [inp("pixels", "IMAGE", scaled_to_encode), inp("vae", "VAE", vae_to_encode)], [out("LATENT", "LATENT", [latent_to_sampler], 0)], [], f"{label} VAEEncode"),
            node(
                sampler_id,
                "KSampler",
                [2420, y + 80],
                [315, 262],
                [
                    inp("model", "MODEL", model_to_sampler),
                    inp("positive", "CONDITIONING", apply_to_sampler_pos),
                    inp("negative", "CONDITIONING", apply_to_sampler_neg),
                    inp("latent_image", "LATENT", latent_to_sampler),
                ],
                [out("LATENT", "LATENT", [sampler_to_decode], 0)],
                [100000 + i, "randomize", 8, 2.0, "dpmpp_sde", "karras", denoise],
                f"{label} Sampler",
            ),
            node(decode_id, "VAEDecode", [2780, y + 140], [210, 46], [inp("samples", "LATENT", sampler_to_decode), inp("vae", "VAE", vae_to_decode)], [out("IMAGE", "IMAGE", [decode_to_preview], 0)], [], f"{label} Decode"),
            node(preview_id, "PreviewImage", [3030, y + 60], [300, 240], [inp("images", "IMAGE", decode_to_preview)], [], [], f"{label} Preview"),
        ]
    )

# Chain ImageBatch nodes to create one 6-image batch, then save it. ComfyUI SaveImage will write all six
# images with the same prefix; this is still useful as a single Queue Prompt comparison run.
batch_ids = [100, 101, 102, 103, 104]
batch_link_ids = []
first_batch = add_link(branch_start + 5, 0, 100, 0, "IMAGE")
second_batch = add_link(branch_start + 7 + 5, 0, 100, 1, "IMAGE")
batch_link_ids.append(first_batch)
batch_link_ids.append(second_batch)
prev_batch_output = add_link(100, 0, 101, 0, "IMAGE")
nodes.append(node(100, "ImageBatch", [3380, 100], [210, 60], [inp("image1", "IMAGE", first_batch), inp("image2", "IMAGE", second_batch)], [out("IMAGE", "IMAGE", [prev_batch_output], 0)], [], "Batch 1-2"))

for j in range(1, 5):
    source_decode_id = branch_start + (j + 1) * 7 + 5
    source_link = add_link(source_decode_id, 0, batch_ids[j], 1, "IMAGE")
    output_link = add_link(batch_ids[j], 0, batch_ids[j + 1], 0, "IMAGE") if j < 4 else add_link(batch_ids[j], 0, 200, 0, "IMAGE")
    nodes.append(node(batch_ids[j], "ImageBatch", [3380, 100 + j * 120], [210, 60], [inp("image1", "IMAGE", prev_batch_output), inp("image2", "IMAGE", source_link)], [out("IMAGE", "IMAGE", [output_link], 0)], [], f"Batch add {j + 2}"))
    prev_batch_output = output_link

nodes.append(node(200, "SaveImage", [3660, 390], [320, 270], [inp("images", "IMAGE", prev_batch_output)], [], ["comfy_flux_platform/six_style_variants_ui"], "Save 6 Variants"))

# Rebuild output link lists from the canonical link table. This keeps the UI graph display correct even
# when a node output gained extra links after the node was initially created.
links_by_origin: dict[tuple[int, int], list[int]] = {}
for link in links:
    link_id, origin_id, origin_slot = link[0], link[1], link[2]
    links_by_origin.setdefault((origin_id, origin_slot), []).append(link_id)
for item in nodes:
    for output in item.get("outputs", []):
        slot = output.get("slot_index", 0)
        output["links"] = links_by_origin.get((item["id"], slot)) or None

workflow = {
    "last_node_id": 200,
    "last_link_id": next_link_id - 1,
    "nodes": nodes,
    "links": links,
    "groups": [
        {"title": "Shared input / model / ControlNet", "bounding": [20, 40, 1450, 760], "color": "#3f789e", "font_size": 24},
        {"title": "Six editable style branches", "bounding": [1500, 20, 1840, 2200], "color": "#8a6fb0", "font_size": 24},
        {"title": "Batch save", "bounding": [3350, 60, 680, 920], "color": "#b58b2b", "font_size": 24},
    ],
    "config": {},
    "extra": {"ds": {"scale": 0.45, "offset": [20, 20]}},
    "version": 0.4,
}

target = Path(__file__).resolve().parents[1] / "workflows" / "six_style_variants_ui.json"
target.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
print(target)
