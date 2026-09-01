from __future__ import annotations

from calliope.config import settings
from calliope.db import get_db


def test_retry_assigns_enabled_workflow_when_original_is_missing(client):
    client.post("/api/jobs/pause")
    project = client.post("/api/projects", json={"title": "Retry workflow"}).json()
    workflow = client.post(
        "/api/workflows",
        json={
            "name": "Recovery image",
            "kind": "image",
            "workflow_json": {
                "1": {
                    "class_type": "PrimitiveString",
                    "inputs": {"value": ""},
                    "_meta": {"title": "(Input:prompt) Prompt"},
                }
            },
        },
    ).json()
    job = client.post(
        f"/api/jobs?project_id={project['id']}",
        json={"kind": "image"},
    ).json()
    conn = get_db(settings.db_path)
    conn.execute("UPDATE jobs SET status = 'failed' WHERE id = ?", (job["id"],))
    conn.commit()
    conn.close()

    retried = client.post(f"/api/jobs/{job['id']}/retry")

    assert retried.status_code == 200
    assert retried.json()["workflow_id"] == workflow["id"]
    client.post("/api/jobs/resume")
