"""Best-effort coordination of local LLM and ComfyUI GPU memory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlparse

import httpx

from calliope.config import settings


def is_local_endpoint(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.hostname in {"localhost", "127.0.0.1", "::1"}


async def release_comfyui_memory() -> None:
    if settings.model_memory_mode != "auto":
        return
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.post(
                f"{settings.comfyui_base_url.rstrip('/')}/free",
                json={"unload_models": True, "free_memory": True},
            )
            response.raise_for_status()
    except Exception:
        # Memory release is an optimization; a failed control request must not
        # prevent the actual LLM request from running.
        return


async def unload_local_llm(base_url: str, model: str) -> None:
    if settings.model_memory_mode != "auto" or not is_local_endpoint(base_url):
        return
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            await client.post(f"{root}/api/v1/models/unload", json={"model": model})
    except Exception:
        return


@asynccontextmanager
async def local_llm_memory_guard(base_url: str, model: str):
    if settings.model_memory_mode == "auto" and is_local_endpoint(base_url):
        from calliope.queue.manager import queue_manager

        was_paused = queue_manager.paused
        queue_manager.paused = True
        await release_comfyui_memory()
        try:
            yield
        finally:
            if not was_paused:
                queue_manager.paused = False
    else:
        yield


async def prepare_comfyui_memory() -> None:
    if settings.model_memory_mode != "auto":
        return
    # LM Studio exposes the unload endpoint when its local server is enabled.
    # The call is intentionally best-effort for installations without it.
    await unload_local_llm(settings.llm_base_url, settings.llm_model)
