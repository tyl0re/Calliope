# ComfyUI Node Setup

Calliope communicates with ComfyUI through its HTTP API. A workflow is usable only when every `class_type` in its API-format JSON is registered by the running ComfyUI instance.

## Install The Supported Node Bundle

From the repository root:

```bash
python scripts/install_comfy_nodes.py --comfyui /path/to/ComfyUI
```

On Windows PowerShell:

```powershell
python scripts/install_comfy_nodes.py --comfyui C:\path\to\ComfyUI
```

The installer is idempotent. It pins `ComfyUI-krea2-negpip` to reviewed commit `3740add9dbdc9f254a2befda30e95ba95e3b115d`, installs it into `custom_nodes`, and installs its `requirements.txt` when present using ComfyUI's detected Python. If detection chooses the wrong interpreter, pass `--python /path/to/ComfyUI/.venv/bin/python` explicitly. Restart ComfyUI after installing a node, then refresh the browser.

## Krea 2 Local Workflows

The local FP8 Krea workflows use these nodes:

- `ApplyKrea2NegPiP` from [ComfyUI-krea2-negpip](https://github.com/blue-pen5805/ComfyUI-krea2-negpip)
- Core ComfyUI loaders, samplers, and `SaveImage`
- `LoraLoader` for the optional refusal-reduction LoRA
- `LoraLoaderModelOnly` for the optional realism LoRA

Portable API-format examples are included in `example_ComfyUI_workflows/`:

- `krea2_character_sheet_local_fp8_uncensored_API.json`
- `krea2_text_to_image_local_fp8_uncensored_API.json`
- `krea2_character_sheet_local_fp8_standard_API.json`
- `krea2_text_to_image_local_fp8_standard_API.json`

The non-local API examples are `krea2_character_sheet_api.json` and `krea2_text_to_image_api.json`. They require a Comfy account/API key because `Krea2ImageNode` is a partner API node. API mode sends prompts and generated images through that third-party service; local mode does not.

The examples refer only to model filenames, not absolute paths. Install the matching model and LoRA files in ComfyUI's model directories before importing them.

### Model Files

The local examples expect the following files in ComfyUI's model directories:

- `models/unet/krea2_turbo_fp8.safetensors` from [AlperKTS/Krea2_FP8](https://huggingface.co/AlperKTS/Krea2_FP8)
- `models/loras/krea2/Krea2-realism-V2.safetensors` for the realism pass
- `models/loras/krea2/Krea2_TextFusion_Refusal_Reduction.safetensors` for the Uncensored variants
- `models/clip/qwen3vl_4b_fp8_scaled.safetensors` for the Krea-2 text encoder
- `models/vae/qwen_image_vae.safetensors` for the Krea-2 VAE

The FP8 workflow is intended for a CUDA GPU with approximately 20 GB or more of available VRAM at 1024-class output. The model and LoRAs are third-party downloads with their own licenses and terms. The Uncensored workflow is not a moderation bypass for hosted APIs; it is a local checkpoint/LoRA choice.

The NegPiP node must be connected after the model and CLIP LoRA loaders and before the text encoders/sampler. Negative terms are encoded as weighted prompt terms such as `(anime:-1.0)`. The local Krea-2 Turbo workflow keeps CFG at `1`, which is the model's stable operating point. The required Krea-specific node is loaded only after ComfyUI is restarted.

## Video Workflows

The MiniMax H3 examples require the H3-related custom nodes shown by ComfyUI's `/object_info` endpoint. Install the corresponding node packages through ComfyUI Manager or your normal node-management process before importing those workflows.

The text-only H3 T2V/Playground example can use the community INT8 ConvRot text encoder
`qwen3vl_32b_minimax_h3_int8_convrot_uncensored-by-linjian257.safetensors`. Download it from [linjian257's repository](https://huggingface.co/linjian257/qwen3vl_32b_minimax_h3_int8_convrot_uncensored-by-linjian257) into `models/text_encoders/minimax-h3/`, then refresh or restart ComfyUI. It is a 24 GiB text-encoder component, not a complete video model; the H3 diffusion model, video VAE, and workflow nodes are still required. The repository is community-provided and uses a personal-entertainment-use-only license. The `uncensored` label is not a guarantee for every prompt or generation.

Reference-to-video and image-to-video examples use the compatible stock H3 INT8 ConvRot encoder because the community encoder's visual path currently requires an unavailable `bfloat16` dequantization backend in ComfyUI. The text-to-video/Playground workflow can use the community encoder. Matching the diffusion-model quantization does not fix this; the text encoder itself would need a new compatible quantized artifact. All H3 text-to-video and image-to-video examples require the Comfy-Org pruned FP8 FL2VA diffusion model `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` in `models/unet/minimax-h3/` and `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors` in `models/loras/minimax-h3/`. The Playground workflows use a direct `VAE Decode → VHS_VideoCombine` path and do not require the optional LTX/upscaling post-processing branch.

The optional `minimax_h3_fastvideo_t2v_uncensored_API.json` workflow uses the Kijai VSA/DataFree four-step checkpoint, the Uncensored H3 textencoder on CPU, and no realism LoRA to reduce peak VRAM. It is a text-to-video speed path, not a replacement for reference-image workflows.

To enable the community encoder's visual path, apply the narrow compatibility patch after installing ComfyUI:

```bash
python scripts/patch_comfy_kitchen_embedding.py --comfyui /path/to/ComfyUI
```

The script creates a `.calliope.bak` backup, is idempotent, and refuses to patch an unexpected source layout. Restart ComfyUI after applying it. This is an experimental compatibility workaround; if it fails or produces unstable output, restore the backup and use the stock encoder for R2V/I2V.

## Adding Another Required Node

Add a new allowlisted entry to `NODE_REPOSITORIES` in `scripts/install_comfy_nodes.py`, using a stable HTTPS repository URL and a directory name. Document the node, its hardware/OS requirements, and the workflow connection in this file. Do not add machine-local paths, credentials, model files, or generated databases to the repository.

## Troubleshooting

1. Restart ComfyUI after installing or updating a custom node.
2. Refresh the ComfyUI browser with `Ctrl+F5`.
3. Check `http://127.0.0.1:8188/object_info` and confirm the workflow's `class_type` values are present.
4. Check the Calliope job error for the exact missing node or invalid input.
