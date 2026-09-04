# Workflow Feature Changes

This document records the behavior changes prepared for review in the `tyl0re/Calliope` fork. It is intentionally implementation-oriented so each change can be traced to a user-visible problem and reproduced by another contributor.

## LLM Compatibility

Codex-backed OpenAI bridge models reject the legacy `temperature` request parameter. Calliope now omits `temperature` for `b-openai/*` and `*codex*` models in both streaming and non-streaming requests. Other models retain the existing sampling behavior.

## Asset Prompt Editing

Characters, locations, and items now persist their optional `negative_prompt` in SQLite. The value is loaded after a browser reload, saved on explicit save and on field blur, and included in subsequent asset jobs. The shared workflow form does not duplicate the per-asset prompt or negative prompt.

The local Krea-2 Turbo workflow uses the NegPiP node. Per-asset negative terms are converted to NegPiP weights in the positive conditioning text while the explicit negative CLIP input is retained. This avoids unstable high-CFG behavior in the Turbo checkpoint.

## Reproducible Asset Seeds

Asset cards expose a `Random seed` toggle. Enabled jobs receive a cryptographically generated KSampler seed in the queue worker; disabled jobs retain the workflow's fixed seed. The behavior also applies to batch asset generation.

## Krea 2 Local/API Selection

Settings expose a persisted Krea 2 generation mode. Asset workflow selection follows the chosen mode and preserves values when switching between workflow schemas by matching canonical input roles. Local and API workflow variants are kept separate so a contributor can choose cloud/API execution or local FP8 execution without editing source code.

## Script And Stage Navigation

Assets now link forward to Script, and Script links forward to Video. Regenerating a script calls the project endpoint directly, confirms before replacing the scene list, and uses the project's target duration to determine the scene count. Script generation has no random seed; variability comes from the configured LLM sampling settings.

Script regeneration no longer preserves an accidentally oversized existing board when `replace=true`. It uses the duration-based recommendation unless the caller explicitly requests a scene count, then normalizes each returned `duration_sec` so the scene durations add up to the requested runtime instead of inheriting one repeated model value.

The script prompt now asks the LLM for editorial durations inside the configurable min/max range based on action complexity, dialogue, reveals, reactions, and transitions. The default range is 4–30 seconds, with no forced target average. Scene-count recommendations use the midpoint of the configured range, while normalization preserves the LLM's relative recommendations and fits the project's target runtime.

Script scene cards expose current character and location links as editable controls. Existing assets can be added or removed without regenerating the script, and the continuation mode is a persisted `New clip`/`Continue from previous video` choice used by subsequent video generation.

Scene asset links also include Items. Item images and descriptions participate in H3 reference ordering, so an explicitly linked object can become `<Subject N>` instead of remaining only text in the scene prompt. H3 templates currently support up to five image references; larger sets are rejected or require a workflow with additional slots.

## Post-Render Video Prompt Editing

The Video stage keeps the prompt and input payload for each render job. After a clip has been rendered, contributors can open **View prompt & inputs**, select a job from the scene history, choose **Edit prompt**, and regenerate with a revised prompt. Saving the revised prompt updates the scene draft so future generations reuse it. The separate **Regenerate** action forces a fresh LLM rewrite instead of returning the existing draft.

Prompt drafts also record the workflow they were generated for. Changing from a one-reference workflow to a multi-reference workflow therefore invalidates the old draft and rebuilds the prompt with every wired subject. The Video stage selects a reference workflow with enough image slots for the scene's available character and location assets when no explicit workflow choice exists.

## Video Workflow Defaults

Video selection no longer falls back to the newest workflow by list order. It uses the lowest enabled workflow ID when a scene has no stored selection, preventing specialized image-to-video or continuation workflows from becoming accidental defaults. Missing optional `SolAttnPatch` nodes were removed from affected workflows because the indexed package is AMD ROCm/Linux-specific and is not suitable as a Windows/NVIDIA dependency.

Video activity events use the stable scene order as a clip label, for example `Clip #4 · INT. APARTMENT - NIGHT`. The label is included in queue creation, start, wait, completion, failure, and H3 rewrite events so the Activity panel and Agent Log can be matched to the timeline.

## Film Quality And Continuity

Video reference wiring is now ordered by the scene relationship order and prose workflows receive all available character/location reference images instead of only the first character image. Subject descriptions prefer the reusable Story appearance/description fields over asset-layout instructions, preventing character-sheet directions from leaking into shot prompts. Video jobs reject workflows that complete without a video file, and random-seed handling covers KSampler, KSamplerAdvanced, RandomNoise, and tagged API seed inputs.

## Playground Artifact Editing

Clicking a Playground artifact opens its recorded prompt and generation settings below the artifact rail. The media remains a playback action; an explicit **Edit** control unlocks the prompt and editable numeric/text settings such as duration. **Regenerate with new seed** creates a new job while preserving the original artifact. Settings are read from the persisted job payload, so the editor also works for workflows that are no longer enabled.

Generate-all persists every resolved scene prompt and its workflow identity before queueing the render. This keeps prompt history available after batch generation and prevents a workflow change from silently reusing a stale prompt draft.

## Local Model Memory Mode

Settings expose `Automatic unload / release` and `Manual memory management`. Automatic mode releases ComfyUI models before local LLM calls and attempts to unload local LM Studio models before ComfyUI jobs. OpenAI-compatible API profiles do not trigger unload operations. Control requests are best-effort and time-limited so an unavailable local service does not block the main job indefinitely.

The default agent step budget is 48 so a complete story-to-script orchestration can finish without requiring a manual setting change. The budget remains configurable for smaller deployments.

MiniMax-H3 examples use the community INT8 ConvRot uncensored text encoder as a drop-in `CLIPLoader` replacement. Its visual path requires the documented BF16 embedding compatibility patch because matching the diffusion-model quantization alone does not fix the text-encoder limitation. This changes the text-encoder component only; it does not remove all model, provider, or workflow-level safety behavior.

The Playground T2V/I2V examples use the Comfy-Org pruned FP8 FL2VA diffusion model and matching four-step LoRA. Their standard output path is intentionally direct to `VHS_VideoCombine`; optional LTX-2 and RTX post-processing dependencies are not required for the baseline render.

An optional FastVideo four-step T2V workflow is included for faster local iteration. It uses the Kijai VSA/DataFree INT8 checkpoint, keeps the Uncensored H3 textencoder on CPU, and disables the realism LoRA to avoid VRAM spikes. It is intentionally separate from the reference-image workflows because FastVideo is a text-only speed path.

## Security And Portability

API credentials are kept in ignored local configuration and are exposed through public settings only as boolean presence flags. The ComfyUI API key is passed to API nodes through `extra_data`, never logged or returned. No model weights, generated media, SQLite databases, absolute machine paths, or user-specific configuration are part of this change set.
