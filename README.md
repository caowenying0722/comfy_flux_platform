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

## 4.1 Flux2 Dev FP8 下载与加载

Flux2 推荐先使用 FP8 版本在 RTX 3090 24GB 上验证。执行：

```bash
cd /mnt/DATA1/zhangshanshan/workspace/comfy_flux_platform
./scripts/install_comfyui.sh
./scripts/download_flux2_models.sh flux2-dev-fp8
```

脚本默认要求目标盘至少有 50GB 空闲空间，避免大模型下载过程中把磁盘写满。确认为安全后可降低阈值：

```bash
MIN_FREE_GB=35 ./scripts/download_flux2_models.sh flux2-dev-fp8
```

脚本会下载到独立 ComfyUI 目录：

```text
ComfyUI/models/text_encoders/mistral_3_small_flux2_fp8.safetensors
ComfyUI/models/diffusion_models/flux2_dev_fp8mixed.safetensors
ComfyUI/models/vae/flux2-vae.safetensors
ComfyUI/models/loras/Flux2TurboComfyv2.safetensors
ComfyUI/user/default/workflows/image_flux2_fp8.json
```

如果 Hugging Face 要求登录或授权：

```bash
export HF_TOKEN=你的HuggingFaceToken
./scripts/download_flux2_models.sh flux2-dev-fp8
```

启动 ComfyUI：

```bash
./scripts/start_comfyui.sh
```

然后打开 ComfyUI，加载：

```text
ComfyUI/user/default/workflows/image_flux2_fp8.json
```

确认单张图能跑通后，导出 API 格式 workflow，放到本项目 `workflows/` 下。后端只要求 workflow 是 ComfyUI `/prompt` 接口能接受的 API JSON。

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
ComfyUI/models/upscale_models/4x-UltraSharp.pth
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
