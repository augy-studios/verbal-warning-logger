from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..database import get_polls_db, get_templates_db

router = APIRouter()


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    options: list[str]
    is_anonymous: bool = False
    max_votes: int = 0


class TemplateUpdate(BaseModel):
    name: str
    description: str = ""
    option_labels: list[str]


def row_to_dict(row) -> dict:
    return dict(row)


@router.get("")
async def list_templates(
    filter: str = "active",
    _user: dict = Depends(get_current_user),
):
    async with get_templates_db() as db:
        if filter == "active":
            cursor = await db.execute(
                "SELECT * FROM poll_templates WHERE is_deleted=0 ORDER BY id DESC"
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM poll_templates ORDER BY id DESC"
            )
        rows = await cursor.fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("")
async def create_template(
    body: TemplateCreate,
    user: dict = Depends(get_current_user),
):
    if len(body.options) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 options required")
    if len(body.options) > 24:
        raise HTTPException(status_code=400, detail="Maximum 24 options allowed")

    async with get_templates_db() as db:
        cursor = await db.execute(
            """INSERT INTO poll_templates
               (name, description, created_by, is_anonymous, max_votes)
               VALUES (?, ?, ?, ?, ?)""",
            (body.name, body.description, int(user["sub"]), int(body.is_anonymous), body.max_votes),
        )
        template_id = cursor.lastrowid
        for i, label in enumerate(body.options):
            await db.execute(
                "INSERT INTO poll_template_options (template_id, label, display_order) VALUES (?, ?, ?)",
                (template_id, label, i),
            )
        await db.commit()

    return await _get_template_full(template_id)


@router.post("/from-poll/{poll_id}")
async def template_from_poll(
    poll_id: int,
    user: dict = Depends(get_current_user),
):
    async with get_polls_db() as db:
        cursor = await db.execute(
            "SELECT * FROM staffpoll_polls WHERE id=?", (poll_id,)
        )
        poll = await cursor.fetchone()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        cursor = await db.execute(
            "SELECT label FROM staffpoll_options WHERE poll_id=? ORDER BY display_order",
            (poll_id,),
        )
        options = await cursor.fetchall()

    async with get_templates_db() as db:
        cursor = await db.execute(
            """INSERT INTO poll_templates
               (name, description, created_by, is_anonymous, max_votes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                poll["title"],
                poll["description"],
                int(user["sub"]),
                poll["is_anonymous"],
                poll["max_votes"],
            ),
        )
        template_id = cursor.lastrowid
        for i, opt in enumerate(options):
            await db.execute(
                "INSERT INTO poll_template_options (template_id, label, display_order) VALUES (?, ?, ?)",
                (template_id, opt["label"], i),
            )
        await db.commit()

    return await _get_template_full(template_id)


@router.get("/{template_id}")
async def get_template(template_id: int, _user: dict = Depends(get_current_user)):
    result = await _get_template_full(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    body: TemplateUpdate,
    _user: dict = Depends(get_current_user),
):
    async with get_templates_db() as db:
        cursor = await db.execute(
            "UPDATE poll_templates SET name=?, description=? WHERE id=?",
            (body.name, body.description, template_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")

        cursor = await db.execute(
            "SELECT id FROM poll_template_options WHERE template_id=? ORDER BY display_order",
            (template_id,),
        )
        options = await cursor.fetchall()
        if len(options) != len(body.option_labels):
            raise HTTPException(status_code=400, detail="Option count mismatch")
        for opt, label in zip(options, body.option_labels):
            await db.execute(
                "UPDATE poll_template_options SET label=? WHERE id=?",
                (label, opt["id"]),
            )
        await db.commit()

    return await _get_template_full(template_id)


@router.delete("/{template_id}")
async def delete_template(template_id: int, _user: dict = Depends(get_current_user)):
    async with get_templates_db() as db:
        cursor = await db.execute(
            "UPDATE poll_templates SET is_deleted=1 WHERE id=?", (template_id,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True, "id": template_id}


@router.post("/{template_id}/restore")
async def restore_template(template_id: int, _user: dict = Depends(get_current_user)):
    async with get_templates_db() as db:
        cursor = await db.execute(
            "UPDATE poll_templates SET is_deleted=0 WHERE id=?", (template_id,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")
    return await _get_template_full(template_id)


@router.post("/{template_id}/use")
async def use_template(
    template_id: int,
    body: dict = {},
    user: dict = Depends(get_current_user),
):
    result = await _get_template_full(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    if result["is_deleted"]:
        raise HTTPException(status_code=400, detail="Template is deleted")

    is_anonymous = body.get("is_anonymous", result["is_anonymous"])
    max_votes = body.get("max_votes", result["max_votes"])
    option_labels = [o["label"] for o in result["options"]]

    async with get_polls_db() as db:
        cursor = await db.execute(
            """INSERT INTO staffpoll_polls
               (title, description, created_by, is_anonymous, max_votes)
               VALUES (?, ?, ?, ?, ?)""",
            (result["name"], result["description"], int(user["sub"]), int(is_anonymous), max_votes),
        )
        poll_id = cursor.lastrowid
        for i, label in enumerate(option_labels):
            await db.execute(
                "INSERT INTO staffpoll_options (poll_id, label, display_order) VALUES (?, ?, ?)",
                (poll_id, label, i),
            )
        await db.commit()

    # Import to avoid circular
    from .polls import _get_poll_full
    return await _get_poll_full(poll_id)


async def _get_template_full(template_id: int) -> dict | None:
    async with get_templates_db() as db:
        cursor = await db.execute(
            "SELECT * FROM poll_templates WHERE id=?", (template_id,)
        )
        template = await cursor.fetchone()
        if not template:
            return None
        cursor = await db.execute(
            "SELECT * FROM poll_template_options WHERE template_id=? ORDER BY display_order",
            (template_id,),
        )
        options = await cursor.fetchall()

    return {**dict(template), "options": [dict(o) for o in options]}
