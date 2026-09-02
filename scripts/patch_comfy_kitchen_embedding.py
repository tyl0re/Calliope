#!/usr/bin/env python3
"""Enable BF16 fallback for community INT8 ConvRot embeddings in ComfyUI.

This narrowly scoped compatibility patch is needed by the community
MiniMax-H3 uncensored text encoder when its visual path retains BF16 tables.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


MARKER = "# Calliope BF16 embedding compatibility fallback"
ANCHOR = "        output_dtype_code = _INT8_DEQUANT_DTYPE_TO_CODE.get(params.orig_dtype, 0)"
INSERT = """        # Calliope BF16 embedding compatibility fallback
        if qdata.dtype != torch.int8:
            return torch.nn.functional.embedding(indices, qdata).to(params.orig_dtype)
"""


def locate_module(comfyui: Path) -> Path:
    candidates = (
        comfyui / ".venv" / "Lib" / "site-packages" / "comfy_kitchen" / "tensor" / "int8.py",
        comfyui / ".venv" / "lib" / "python3.12" / "site-packages" / "comfy_kitchen" / "tensor" / "int8.py",
        comfyui / "venv" / "Lib" / "site-packages" / "comfy_kitchen" / "tensor" / "int8.py",
        comfyui / "venv" / "lib" / "python3.12" / "site-packages" / "comfy_kitchen" / "tensor" / "int8.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate comfy_kitchen/tensor/int8.py")


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    function_start = text.index("    def dequantize_embedding(")
    anchor_at = text.index(ANCHOR, function_start)
    backup = path.with_suffix(path.suffix + ".calliope.bak")
    shutil.copy2(path, backup)
    patched = text[:anchor_at] + INSERT + text[anchor_at:]
    path.write_text(patched, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfyui", type=Path, required=True)
    args = parser.parse_args()
    if not args.comfyui.is_dir():
        parser.error(f"ComfyUI directory does not exist: {args.comfyui}")
    path = locate_module(args.comfyui)
    print(f"Patched: {path}" if patch(path) else f"Already patched: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
