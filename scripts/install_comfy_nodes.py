#!/usr/bin/env python3
"""Install the ComfyUI custom nodes used by the documented workflows.

The installer is intentionally dependency-light and does not assume a Windows
path, a particular Python environment, or an activated ComfyUI virtualenv.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


NODE_REPOSITORIES = {
    "krea2-negpip": (
        "https://github.com/blue-pen5805/ComfyUI-krea2-negpip.git",
        "ComfyUI-krea2-negpip",
        "3740add9dbdc9f254a2befda30e95ba95e3b115d",
    ),
}


def _comfy_python(comfyui_dir: Path, explicit: Path | None) -> Path:
    if explicit:
        if not explicit.is_file():
            raise RuntimeError(f"ComfyUI Python executable does not exist: {explicit}")
        return explicit

    candidates = (
        comfyui_dir / ".venv" / "Scripts" / "python.exe",
        comfyui_dir / ".venv" / "bin" / "python",
        comfyui_dir / "venv" / "Scripts" / "python.exe",
        comfyui_dir / "venv" / "bin" / "python",
        comfyui_dir / "python_embeded" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "Could not find ComfyUI's Python executable. "
        "Pass --python /path/to/comfy/python explicitly."
    )


def install_node(comfyui_dir: Path, node_name: str, python: Path) -> None:
    repository, directory_name, commit = NODE_REPOSITORIES[node_name]
    target = comfyui_dir / "custom_nodes" / directory_name
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        if not (target / ".git").exists():
            raise RuntimeError(f"Refusing to overwrite non-git directory: {target}")
        current = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if current != commit:
            raise RuntimeError(
                f"{node_name} is installed at {current}; expected reviewed commit {commit}. "
                "Update it manually after reviewing the new commit."
            )
        for command in (("diff", "--quiet"), ("diff", "--cached", "--quiet")):
            if subprocess.run(["git", "-C", str(target), *command], check=False).returncode != 0:
                raise RuntimeError(f"Refusing to install from modified checkout: {target}")
        print(f"Already installed: {node_name} ({target})")
    else:
        subprocess.run(
            ["git", "clone", "--depth", "1", repository, str(target)],
            check=True,
        )
        subprocess.run(["git", "-C", str(target), "fetch", "--depth", "1", "origin", commit], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", commit], check=True)

    requirements = target / "requirements.txt"
    if requirements.is_file():
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(requirements)],
            check=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comfyui",
        type=Path,
        required=True,
        help="Path to the ComfyUI installation",
    )
    parser.add_argument(
        "--node",
        choices=["all", *NODE_REPOSITORIES],
        default="all",
        help="Node bundle to install (default: all)",
    )
    parser.add_argument(
        "--python",
        type=Path,
        help="ComfyUI's Python executable; auto-detected when omitted",
    )
    args = parser.parse_args()

    if not args.comfyui.is_dir():
        parser.error(f"ComfyUI directory does not exist: {args.comfyui}")

    selected = NODE_REPOSITORIES if args.node == "all" else {args.node: NODE_REPOSITORIES[args.node]}
    python = _comfy_python(args.comfyui, args.python)
    for node_name in selected:
        install_node(args.comfyui, node_name, python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
