from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..database import get_polls_db

router = APIRouter()


class PollCreate(BaseModel):
    title: str
    description: str = ""
    options: list[str]
    is_anonymous: bool = False
    max_votes: int = 0


class PollUpdate(BaseModel):
    title: str
    description: str = ""
    option_labels: list[str]


def row_to_dict(row) -> dict:
    return dict(row)


@router.get("")
async def list_polls(
    filter: str = "active",
    page: int = 1,
    per_page: int = 20,
    _user: dict = Depends(get_current_user),
):
    async with get_polls_db() as db:
        if filter == "active":
            cursor = await db.execute(
                "SELECT * FROM staffpoll_polls WHERE is_active=1 ORDER BY id DESC"
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM staffpoll_polls ORDER BY id DESC"
            )
        all_rows = await cursor.fetchall()

    total = len(all_rows)
    offset = (page - 1) * per_page
    rows = all_rows[offset : offset + per_page]
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": [row_to_dict(r) for r in rows],
    }


@router.post("")
async def create_poll(
    body: PollCreate,
    user: dict = Depends(get_current_user),
):
    if len(body.options) < 2:
        raise HTTPException(status_code=400, detail="Minimum 2 options required")
    if len(body.options) > 24:
        raise HTTPException(status_code=400, detail="Maximum 24 options allowed")

    async with get_polls_db() as db:
        cursor = await db.execute(
            """INSERT INTO staffpoll_polls
               (title, description, created_by, is_anonymous, max_votes)
               VALUES (?, ?, ?, ?, ?)""",
            (body.title, body.description, int(user["sub"]), int(body.is_anonymous), body.max_votes),
        )
        poll_id = cursor.lastrowid

        for i, label in enumerate(body.options):
            await db.execute(
                "INSERT INTO staffpoll_options (poll_id, label, display_order) VALUES (?, ?, ?)",
                (poll_id, label, i),
            )
        await db.commit()

    return await _get_poll_full(poll_id)


@router.get("/stats")
async def poll_stats(_user: dict = Depends(get_current_user)):
    async with get_polls_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as total FROM staffpoll_polls")
        total = (await cursor.fetchone())["total"]

        cursor = await db.execute(
            "SELECT COUNT(*) as active FROM staffpoll_polls WHERE is_active=1"
        )
        active = (await cursor.fetchone())["active"]

        cursor = await db.execute("SELECT COUNT(*) as votes FROM staffpoll_votes")
        votes = (await cursor.fetchone())["votes"]

    return {"total": total, "active": active, "total_votes": votes}


@router.get("/{poll_id}")
async def get_poll(poll_id: int, _user: dict = Depends(get_current_user)):
    result = await _get_poll_full(poll_id)
    if not result:
        raise HTTPException(status_code=404, detail="Poll not found")
    return result


@router.put("/{poll_id}")
async def update_poll(
    poll_id: int,
    body: PollUpdate,
    _user: dict = Depends(get_current_user),
):
    async with get_polls_db() as db:
        cursor = await db.execute(
            "UPDATE staffpoll_polls SET title=?, description=? WHERE id=?",
            (body.title, body.description, poll_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Poll not found")

        # Update option labels (count must match)
        cursor = await db.execute(
            "SELECT id FROM staffpoll_options WHERE poll_id=? ORDER BY display_order",
            (poll_id,),
        )
        options = await cursor.fetchall()
        if len(options) != len(body.option_labels):
            raise HTTPException(
                status_code=400, detail="Option count mismatch — cannot add/remove options"
            )
        for opt, label in zip(options, body.option_labels):
            await db.execute(
                "UPDATE staffpoll_options SET label=? WHERE id=?",
                (label, opt["id"]),
            )
        await db.commit()

    return await _get_poll_full(poll_id)


@router.delete("/{poll_id}")
async def close_poll(poll_id: int, _user: dict = Depends(get_current_user)):
    async with get_polls_db() as db:
        cursor = await db.execute(
            "UPDATE staffpoll_polls SET is_active=0 WHERE id=?", (poll_id,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Poll not found")
    return {"closed": True, "id": poll_id}


@router.post("/{poll_id}/reopen")
async def reopen_poll(poll_id: int, _user: dict = Depends(get_current_user)):
    async with get_polls_db() as db:
        cursor = await db.execute(
            "UPDATE staffpoll_polls SET is_active=1 WHERE id=?", (poll_id,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Poll not found")
    return await _get_poll_full(poll_id)


@router.get("/{poll_id}/results")
async def poll_results(poll_id: int, _user: dict = Depends(get_current_user)):
    async with get_polls_db() as db:
        cursor = await db.execute(
            "SELECT * FROM staffpoll_polls WHERE id=?", (poll_id,)
        )
        poll = await cursor.fetchone()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        cursor = await db.execute(
            "SELECT * FROM staffpoll_options WHERE poll_id=? ORDER BY display_order",
            (poll_id,),
        )
        options = await cursor.fetchall()

        cursor = await db.execute(
            "SELECT option_id, COUNT(*) as count FROM staffpoll_votes WHERE poll_id=? GROUP BY option_id",
            (poll_id,),
        )
        vote_rows = await cursor.fetchall()
        vote_counts = {r["option_id"]: r["count"] for r in vote_rows}

        cursor = await db.execute(
            "SELECT user_id, option_id FROM staffpoll_votes WHERE poll_id=?",
            (poll_id,),
        )
        all_votes = await cursor.fetchall()

    total_votes = sum(vote_counts.values())
    results = []
    for opt in options:
        count = vote_counts.get(opt["id"], 0)
        results.append({
            "id": opt["id"],
            "label": opt["label"],
            "count": count,
            "percentage": round(count / total_votes * 100, 1) if total_votes else 0,
        })

    return {
        "poll": row_to_dict(poll),
        "options": results,
        "total_votes": total_votes,
        "voters": (
            [{"user_id": str(v["user_id"]), "option_id": v["option_id"]} for v in all_votes]
            if not poll["is_anonymous"]
            else []
        ),
    }


async def _get_poll_full(poll_id: int) -> dict | None:
    async with get_polls_db() as db:
        cursor = await db.execute(
            "SELECT * FROM staffpoll_polls WHERE id=?", (poll_id,)
        )
        poll = await cursor.fetchone()
        if not poll:
            return None

        cursor = await db.execute(
            "SELECT * FROM staffpoll_options WHERE poll_id=? ORDER BY display_order",
            (poll_id,),
        )
        options = await cursor.fetchall()

        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM staffpoll_votes WHERE poll_id=?", (poll_id,)
        )
        vote_count = (await cursor.fetchone())["count"]

    return {
        **row_to_dict(poll),
        "options": [row_to_dict(o) for o in options],
        "vote_count": vote_count,
    }
