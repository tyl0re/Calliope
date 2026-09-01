from __future__ import annotations

import json
from pathlib import Path

WORKFLOW_DIR = Path(__file__).parents[2] / "example_ComfyUI_workflows"


def test_example_workflows_are_valid_api_json():
    files = sorted(WORKFLOW_DIR.glob("*.json"))

    assert files
    for path in files:
        workflow = json.loads(path.read_text(encoding="utf-8"))
        for node_id, node in workflow.items():
            assert node.get("class_type"), f"{path.name}:{node_id} missing class_type"
            for value in (node.get("inputs") or {}).values():
                if isinstance(value, list) and value and isinstance(value[0], str):
                    assert value[0] in workflow, f"{path.name}: dangling {node_id} -> {value[0]}"
