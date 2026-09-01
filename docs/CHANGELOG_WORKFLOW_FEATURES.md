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

## Post-Render Video Prompt Editing

The Video stage keeps the prompt and input payload for each render job. After a clip has been rendered, contributors can open **View prompt & inputs**, select a job from the scene history, choose **Edit prompt**, and regenerate with a revised prompt. Saving the revised prompt updates the scene draft so future generations reuse it. The separate **Regenerate** action forces a fresh LLM rewrite instead of returning the existing draft.

## Video Workflow Defaults

Video selection no longer falls back to the newest workflow by list order. It uses the lowest enabled workflow ID when a scene has no stored selection, preventing specialized image-to-video or continuation workflows from becoming accidental defaults. Missing optional `SolAttnPatch` nodes were removed from affected workflows because the indexed package is AMD ROCm/Linux-specific and is not suitable as a Windows/NVIDIA dependency.

## Security And Portability

API credentials are kept in ignored local configuration and are exposed through public settings only as boolean presence flags. The ComfyUI API key is passed to API nodes through `extra_data`, never logged or returned. No model weights, generated media, SQLite databases, absolute machine paths, or user-specific configuration are part of this change set.
