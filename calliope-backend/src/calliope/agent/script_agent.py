"""Generate scene scripts via LLM and persist them."""
from __future__ import annotations

from typing import Any

from calliope.agent.llm import generate_structured
from calliope.agent.prompts import (
    build_script_messages,
    estimate_target_seconds,
    recommend_scene_count,
)
from calliope.config import settings
from calliope.db import get_db, row_to_dict
from calliope.events.bus import event_bus


def _persist_scenes(
    conn,
    project_id: int,
    scenes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for scene in scenes:
        loc_id = scene.get("location_id")
        env_path = None
        if loc_id:
            loc = conn.execute(
                "SELECT reference_image_path FROM locations WHERE id = ? AND project_id = ?",
                (loc_id, project_id),
            ).fetchone()
            if loc:
                env_path = loc["reference_image_path"]

        cur = conn.execute(
            """
            INSERT INTO scenes
            (
                project_id, order_index, heading, action, dialog, duration_sec,
                location_id, env_image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                scene.get("order_index", 0),
                scene.get("heading"),
                scene.get("action"),
                scene.get("dialog"),
                scene.get("duration_sec"),
                loc_id,
                env_path,
            ),
        )
        scene_id = cur.lastrowid
        for cid in scene.get("character_ids") or []:
            exists = conn.execute(
                "SELECT id FROM characters WHERE id = ? AND project_id = ?",
                (cid, project_id),
            ).fetchone()
            if exists:
                conn.execute(
                    "INSERT OR IGNORE INTO scene_characters (scene_id, character_id) VALUES (?, ?)",
                    (scene_id, cid),
                )
        row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        created.append(row_to_dict(row))
    return created


def _normalize_scene_durations(
    scenes: list[dict[str, Any]],
    total_seconds: int,
    min_duration: int = 4,
    max_duration: int = 15,
) -> None:
    if not scenes:
        return
    min_duration = max(1, min(min_duration, max_duration))
    max_duration = max(min_duration, max_duration)
    target = max(total_seconds, len(scenes) * min_duration)
    raw: list[int] = []
    for scene in scenes:
        try:
            value = int(float(scene.get("duration_sec") or 6))
        except (TypeError, ValueError):
            value = 6
        raw.append(max(min_duration, min(max_duration, value)))
    raw_total = sum(raw)
    durations = [
        max(min_duration, min(max_duration, round(value * target / raw_total)))
        for value in raw
    ]
    while sum(durations) < target:
        index = max(range(len(durations)), key=lambda i: (raw[i], -i))
        if durations[index] == max_duration:
            break
        durations[index] += 1
    while sum(durations) > target:
        index = max(range(len(durations)), key=lambda i: (durations[i], raw[i], -i))
        if durations[index] == min_duration:
            break
        durations[index] -= 1
    for scene, duration in zip(scenes, durations):
        scene["duration_sec"] = duration


async def generate_script(
    project_id: int,
    *,
    replace: bool = True,
    scene_count: int | None = None,
) -> dict[str, Any]:
    await event_bus.publish(
        "agent.thinking", {"message": "Writing scene script…", "project_id": project_id}
    )
    conn = get_db(settings.db_path)
    try:
        project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError("Project not found")
        p = row_to_dict(project)
        beats = [
            row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM story_beats WHERE project_id = ? ORDER BY order_index",
                (project_id,),
            ).fetchall()
        ]
        characters = [
            row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM characters WHERE project_id = ?", (project_id,)
            ).fetchall()
        ]
        locations = [
            row_to_dict(r)
            for r in conn.execute(
                "SELECT * FROM locations WHERE project_id = ?", (project_id,)
            ).fetchall()
        ]

        existing_n = conn.execute(
            "SELECT COUNT(*) AS n FROM scenes WHERE project_id = ?",
            (project_id,),
        ).fetchone()["n"]
        recommended = recommend_scene_count(
            p.get("target_duration"), settings.script_target_scene_duration_sec
        )
        # Prefer explicit request, else keep at least the board the user already built
        requested = (
            scene_count if scene_count and scene_count > 0 else existing_n if not replace else 0
        )
        required_scenes = max(recommended, int(requested)) if requested else recommended

        await event_bus.publish(
            "agent.thinking",
            {
                "message": f"Writing {required_scenes} scenes "
                f"(board had {existing_n}; duration suggests {recommended})…",
                "project_id": project_id,
            },
        )

        messages = build_script_messages(
            title=p["title"],
            idea=p.get("idea"),
            beats=beats,
            characters=characters,
            locations=locations,
            target_duration=p.get("target_duration"),
            scene_count=required_scenes,
            min_scene_duration_sec=settings.script_min_scene_duration_sec,
            max_scene_duration_sec=settings.script_max_scene_duration_sec,
            target_scene_duration_sec=settings.script_target_scene_duration_sec,
        )
        result = await generate_structured(messages, temperature=0.7)
        scenes_out = result.get("scenes") or []

        if len(scenes_out) < required_scenes:
            await event_bus.publish(
                "agent.thinking",
                {
                    "message": (
                        f"Model returned {len(scenes_out)} scenes; "
                        f"required {required_scenes}. Retrying…"
                    ),
                    "project_id": project_id,
                },
            )
            retry_messages = [
                messages[0],
                {
                    "role": "user",
                    "content": messages[1]["content"]
                    + (
                        f"\n\nPREVIOUS ATTEMPT FAILED: it only had {len(scenes_out)} scenes. "
                        f"You MUST return exactly {required_scenes} scenes this time."
                    ),
                },
            ]
            result = await generate_structured(retry_messages, temperature=0.5)
            scenes_out = result.get("scenes") or []
            if len(scenes_out) < required_scenes:
                raise ValueError(
                    f"Script returned {len(scenes_out)} scenes but {required_scenes} were "
                    "required. "
                    "Add scenes again and retry, or raise target duration."
                )

        _normalize_scene_durations(
            scenes_out,
            estimate_target_seconds(p.get("target_duration")),
            settings.script_min_scene_duration_sec,
            settings.script_max_scene_duration_sec,
        )

        if replace:
            scene_ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM scenes WHERE project_id = ?", (project_id,)
                ).fetchall()
            ]
            for sid in scene_ids:
                conn.execute("DELETE FROM scene_characters WHERE scene_id = ?", (sid,))
            conn.execute("DELETE FROM scenes WHERE project_id = ?", (project_id,))

        created = _persist_scenes(conn, project_id, scenes_out)

        conn.execute(
            "UPDATE projects SET status = 'in_progress', "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (project_id,),
        )
        conn.commit()
        await event_bus.publish(
            "agent.thinking",
            {
                "message": f"Script written — {len(created)} scenes",
                "project_id": project_id,
            },
        )
        return {"ok": True, "scenes": created, "generated": result}
    finally:
        conn.close()
