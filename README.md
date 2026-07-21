# Comfy Flux Platform

基于 FastAPI + ComfyUI API 的图片生成平台。用户上传图片，选择风格模板，后台调用 ComfyUI workflow 生成多张图片，并通过 workflow 内置 Upscaler 输出高清图片。

项目默认目录：

```bash
/mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
```

## 1. 系统架构

```text
backend/
  main.py                  FastAPI 入口
  api/routes.py            HTTP API
  services/comfyui_client.py
  services/prompt_service.py
  services/storage.py
  services/task_service.py
  models/entities.py       SQLAlchemy ORM
  database/session.py
workflows/
  cinematic.json
  product.json
  anime.json
  figurine3d.json
  guofeng.json
  oilpainting.json
storage/
  original_images/
  generated_images/
data/
  app.db
```

## 2. 安装后端独立环境

不要使用系统 Python 或其他项目的虚拟环境。

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
python -m backend.database.init_db
```

启动：

```bash
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 3. API

### 上传图片

```bash
curl -F "file=@/path/to/input.png" http://127.0.0.1:8000/upload
```

返回：

```json
{"image_id":"...","filename":"input.png"}
```

### 查询风格

```bash
curl http://127.0.0.1:8000/styles
```

### 生成图片

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"image_id":"替换为上传返回ID","style_id":"cinematic","count":5}'
```

`count` 支持 1-20，可覆盖 5、10、20 张批量生成场景。每张图自动使用不同 seed，失败会按 `.env` 的 `GENERATION_MAX_RETRIES` 重试。

### 查询任务

```bash
curl http://127.0.0.1:8000/task/任务ID
```

返回结构：

```json
{
  "status": "pending|generating|completed|failed",
  "images": [
    {"status": "completed", "url": "/files/generated_images/xxx.png"}
  ]
}
```

下载图片：

```bash
curl -O http://127.0.0.1:8000/files/generated_images/xxx.png
```

## 4. ComfyUI 独立部署

建议把 ComfyUI 放在本项目内，避免污染其他项目：

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
./scripts/install_comfyui.sh
```

根据服务器 CUDA/PyTorch 情况安装匹配版本的 torch。如果 requirements 安装了 CPU 版，需要重新安装 CUDA 版 torch。

启动 API/headless：

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform/ComfyUI
source .venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch
```

## 4.1 当前服务器模型兼容性结论

当前宿主机 NVIDIA 驱动为 `470.x`，无法稳定运行当前 Flux/Flux2/Qwen-Image/Z-Image 常用的新 PyTorch + 新 ComfyUI 栈。已验证的可用路线如下：

| 模型路线 | 当前状态 | 原因 |
| --- | --- | --- |
| SDXL base | 已下载并通过后端 E2E 测试 | 旧版 ComfyUI + PyTorch 1.12 可加载 checkpoint 工作流 |
| DreamShaper XL Lightning | 已下载并通过后端 E2E 测试 | SDXL 微调 checkpoint，风格化能力强于 SDXL base |
| SD1.5 | 已下载并通过后端 E2E 测试 | 对旧驱动兼容性最好 |
| Flux/Flux2/FLUX.1-schnell FP8 | 不保留 | 旧 torch 缺少 `torch.float8_e4m3fn` |
| Qwen-Image | 不下载 | 20B 级别新模型，对新 ComfyUI/torch/显存/内存要求高，当前环境不能保证通过 |
| Z-Image | 不下载 | 主流高效运行路径依赖 FP8/Triton/新 torch，当前环境不能保证通过 |

为避免占用磁盘，当前项目未保留 Flux/Qwen/Z-Image 权重。后续如果宿主机驱动升级到可支持 CUDA 12 + PyTorch 2.x，再单独启用现代模型路线。

## 4.2 旧驱动兼容模式：能生图的 SD1.5 路线

如果宿主机 NVIDIA 驱动是 `470.x`，无法稳定运行当前 ComfyUI + Flux/Flux2 所需的新 PyTorch。此时使用旧版 ComfyUI + PyTorch CUDA 11.3：

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
./scripts/install_comfyui_cuda114_legacy.sh
./scripts/download_sd15_legacy.sh
```

启动 ComfyUI：

```bash
./scripts/start_comfyui.sh
```

后端使用：

```json
{"style_id":"sd15_legacy"}
```

已知限制：

- `flux_schnell` FP8 在旧 torch 下无法加载，错误为缺少 `torch.float8_e4m3fn`，因此默认风格中已移除。
- 最新 ComfyUI 在旧 torch 下无法启动，错误为缺少 `torch.library.custom_op`。
- 因此旧驱动下的可落地路线是 SD1.5/部分旧 SDXL 工作流，不是 Flux/Flux2。

## 4.3 SDXL 高质量兼容路线

旧驱动下也可以尝试 SDXL base，质量通常明显高于 SD1.5，但速度更慢、显存占用更高：

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
./scripts/download_sdxl_base.sh
```

后端使用：

```json
{"style_id":"sdxl_base"}
```

模型位置：

```text
ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors
```

最小可用自动图生图 workflow：

```text
LoadImage
→ ImageScale(1024x1024)
→ CheckpointLoaderSimple(sd_xl_base_1.0.safetensors)
→ VAEEncode
→ CLIPTextEncode(prompt / negative_prompt)
→ KSampler(img2img denoise 0.55)
→ VAEDecode
→ SaveImage
```

说明：

- `sd_xl_base_1.0.safetensors` 是完整 SDXL checkpoint，`CheckpointLoaderSimple` 会直接输出 `MODEL / CLIP / VAE`。
- 因此当前最小可用工作流不需要额外下载 CLIP 或 VAE。
- 只有使用分体模型、替换精调 VAE、或切换到 Flux/Qwen/Z-Image 这类新架构时，才需要额外的 text encoder / VAE / diffusion model。
- 当前 `cinematic/product/anime/figurine3d/guofeng/oilpainting/sdxl_base` 风格均复用 `workflows/sdxl_base_img2img.json`，通过不同 prompt 区分风格。

## 4.4 DreamShaper XL 风格化路线

DreamShaper XL Lightning 是基于 SDXL Base 微调的 checkpoint，更偏艺术、动漫和风格化，当前旧驱动环境已验证可运行：

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
./scripts/download_dreamshaper_xl.sh
```

模型位置：

```text
ComfyUI/models/checkpoints/DreamShaperXL_Lightning.safetensors
```

后端使用：

```json
{"style_id":"dreamshaper_pixar"}
```

对应 workflow：

```text
workflows/dreamshaper_xl_img2img.json
```

后端 `.env`：

```env
COMFYUI_BASE_URL=http://127.0.0.1:8188
COMFYUI_WS_URL=ws://127.0.0.1:8188/ws
COMFYUI_MOCK=false
```

无模型或暂时未启动 ComfyUI 时，可以先用 mock 验证后端 API：

```env
COMFYUI_MOCK=true
```

## 5. 模型目录结构

ComfyUI 常用目录：

```text
ComfyUI/models/
  checkpoints/         SDXL checkpoint
  diffusion_models/    Flux/Flux2 diffusion model，部分版本也使用 unet/
  unet/
  vae/
  clip/
  text_encoders/
  upscale_models/      RealESRGAN、4x-UltraSharp
  controlnet/
  ipadapter/
```

当前 workflow 模板默认引用：

```text
ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors
```

如果使用 Flux2，需要在 ComfyUI 中确认已安装对应节点、模型文件和 text encoder，然后从 ComfyUI 导出 API 格式 workflow，保存到 `workflows/*.json`，保留这些占位符：

```text
{{input_image}}
{{prompt}}
{{negative_prompt}}
{{seed}}
{{width}}
{{height}}
{{upscale_factor}}
```

## 6. Workflow 调试方法

1. 在 ComfyUI 页面手工搭建 workflow。
2. 确认单张图能正常生成和放大。
3. 打开 ComfyUI 设置，启用开发者模式或导出 API 格式。
4. 保存 API JSON 到 `workflows/<style>.json`。
5. 将图片输入节点的文件名替换为 `{{input_image}}`。
6. 将正向提示词替换为 `{{prompt}}`。
7. 将反向提示词替换为 `{{negative_prompt}}`。
8. 将 sampler seed 替换为 `{{seed}}`。
9. 调用 `/generate` 测试。

如果 ComfyUI 返回 `invalid prompt`，优先检查：

- workflow 是否是 API 格式，不是 UI 格式。
- `class_type` 是否对应已安装节点。
- checkpoint、vae、clip、upscale model 文件名是否和 ComfyUI 下拉框完全一致。
- 自定义节点是否安装在当前独立 ComfyUI 环境中。

## 7. RTX 3090 24GB 优化建议

推荐基线：

- 生成阶段先用 1024 边长，放大交给 Upscaler。
- 批量任务串行执行，避免 20 张同时占满显存。
- Flux/Flux2 显存压力大时降低 steps、关闭 preview、减少 batch size。
- 优先使用 fp16/bf16 模型权重。
- 使用 ComfyUI 启动参数：`--lowvram` 或 `--normalvram` 视模型大小测试。
- 开启 CPU offload 或使用量化模型时，接受速度下降换显存稳定性。
- 对 Flux2 如 24GB 仍不足：使用量化版本、降低分辨率到 768/896、减少 ControlNet/IPAdapter 组合、先 SDXL fallback。

## 8. 生产存储扩展

当前 `StorageService` 使用本地文件系统：

```text
storage/original_images
storage/generated_images
```

生产环境接 OSS/S3 时，保持 API 返回 `url` 字段不变，只需要替换 `backend/services/storage.py` 的保存和 URL 生成逻辑。

## 9. 注意事项

- 本项目后端、ComfyUI、数据目录、图片目录均在项目内，避免污染其他项目。
- 默认任务队列为单进程内队列；如果多进程运行 Uvicorn workers，需要改成 Redis/Celery/RQ。
- 当前 workflow 是 SDXL img2img 可运行基线，Flux2 节点应以 ComfyUI 实际导出的 API workflow 为准。
