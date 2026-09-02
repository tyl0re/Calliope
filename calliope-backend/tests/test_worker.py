from calliope.comfyui.client import ComfyUIClient
from calliope.queue.worker import randomize_sampler_seeds


def test_randomize_sampler_seeds_only_changes_sampler_seed():
    workflow = {
        "1": {
            "class_type": "KSampler",
            "inputs": {"seed": 123, "steps": 8},
        },
        "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0]}},
    }

    randomized = randomize_sampler_seeds(workflow)

    assert workflow["1"]["inputs"]["seed"] == 123
    assert randomized["1"]["inputs"]["steps"] == 8
    assert randomized["1"]["inputs"]["seed"] != 123
    assert 0 <= randomized["1"]["inputs"]["seed"] < 2**63


def test_video_output_filter_rejects_preview_images():
    assert ComfyUIClient.is_video_output({"filename": "clip.mp4"})
    assert ComfyUIClient.is_video_output({"filename": "clip.webm"})
    assert not ComfyUIClient.is_video_output({"filename": "preview.png"})


def test_randomize_sampler_seeds_handles_api_and_advanced_nodes():
    workflow = {
        "1": {
            "class_type": "PrimitiveInt",
            "inputs": {"value": 0},
            "_meta": {"title": "(Input:seed) Seed"},
        },
        "2": {"class_type": "KSamplerAdvanced", "inputs": {"noise_seed": 10}},
    }

    randomized = randomize_sampler_seeds(workflow)

    assert 0 <= randomized["1"]["inputs"]["value"] < 2**31
    assert 0 <= randomized["2"]["inputs"]["noise_seed"] < 2**63
