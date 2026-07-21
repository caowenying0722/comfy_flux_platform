# Flux2 Dev FP8 workflow

This backend accepts native ComfyUI API prompt JSON files.

Flux2's official ComfyUI example currently ships as a UI workflow with a subgraph. Use:

```bash
./scripts/download_flux2_models.sh flux2-dev-fp8
```

Then in ComfyUI:

1. Load `ComfyUI/user/default/workflows/image_flux2_fp8.json`.
2. Verify a single generation works.
3. Export or save the workflow in API format.
4. Replace or add a JSON file under this project's `workflows/`.
5. Keep these placeholders where relevant:

```text
{{input_image}}
{{prompt}}
{{negative_prompt}}
{{seed}}
{{width}}
{{height}}
{{upscale_factor}}
```

For a single uploaded image, use the same `{{input_image}}` for both Flux2 reference inputs.
