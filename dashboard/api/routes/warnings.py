import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..config import DISCORD_BOT_TOKEN, EMBED_COLOR, LOG_CHANNEL_ID
from ..database import get_warnings_db

router = APIRouter()


class WarningCreate(BaseModel):
    userId: str
    reason: str
    evidenceLink: str
    modId: str


class WarningUpdate(BaseModel):
    userId: str
    reason: str
    evidenceLink: str
    modId: str


def row_to_dict(row) -> dict:
    return dict(row)


def _normalize_evidence_link(link: str) -> str:
    return link.replace("https://canary.discord.com", "https://discord.com")


async def _post_warning_to_log_channel(warning: dict) -> None:
    if not LOG_CHANNEL_ID:
        return
    embed = {
        "title": "Verbal warning added",
        "color": EMBED_COLOR,
        "fields": [
            {"name": "ID", "value": f"`{warning['id']}`", "inline": True},
            {"name": "User", "value": f"<@{warning['userId']}> (`{warning['userId']}`)", "inline": False},
            {"name": "Mod", "value": f"<@{warning['modId']}> (`{warning['modId']}`)", "inline": False},
            {"name": "Evidence", "value": warning["evidenceLink"], "inline": False},
            {"name": "Reason", "value": warning["reason"], "inline": False},
        ],
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
            json={"embeds": [embed]},
        )


@router.get("")
async def list_warnings(
    page: int = 1,
    per_page: int = 20,
    user_id: str | None = None,
    _user: dict = Depends(get_current_user),
):
    async with get_warnings_db() as db:
        if user_id:
            cursor = await db.execute(
                "SELECT * FROM verbal_warnings WHERE userId = ? ORDER BY id DESC",
                (int(user_id),),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM verbal_warnings ORDER BY id DESC"
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
async def create_warning(
    body: WarningCreate,
    _user: dict = Depends(get_current_user),
):
    evidence_link = _normalize_evidence_link(body.evidenceLink)

    async with get_warnings_db() as db:
        cursor = await db.execute(
            "INSERT INTO verbal_warnings (userId, reason, evidenceLink, modId) VALUES (?, ?, ?, ?)",
            (int(body.userId), body.reason, evidence_link, int(body.modId)),
        )
        await db.commit()
        warning_id = cursor.lastrowid

    async with get_warnings_db() as db:
        cursor = await db.execute(
            "SELECT * FROM verbal_warnings WHERE id = ?", (warning_id,)
        )
        row = await cursor.fetchone()

    warning = row_to_dict(row)
    await _post_warning_to_log_channel(warning)
    return warning


@router.get("/stats")
async def get_stats(_user: dict = Depends(get_current_user)):
    async with get_warnings_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as total FROM verbal_warnings")
        total_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT COUNT(*) as count FROM verbal_warnings WHERE createdAt >= date('now', '-7 days')"
        )
        recent_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT userId, COUNT(*) as count FROM verbal_warnings GROUP BY userId ORDER BY count DESC LIMIT 5"
        )
        top_offenders = await cursor.fetchall()

        cursor = await db.execute(
            "SELECT modId, COUNT(*) as count FROM verbal_warnings GROUP BY modId ORDER BY count DESC LIMIT 5"
        )
        top_mods = await cursor.fetchall()

    return {
        "total": total_row["total"],
        "last_7_days": recent_row["count"],
        "top_offenders": [dict(r) for r in top_offenders],
        "top_mods": [dict(r) for r in top_mods],
    }


@router.get("/leaderboard")
async def leaderboard(
    mode: str = "offender",
    _user: dict = Depends(get_current_user),
):
    if mode not in ("offender", "mod"):
        raise HTTPException(status_code=400, detail="mode must be 'offender' or 'mod'")

    field = "userId" if mode == "offender" else "modId"
    async with get_warnings_db() as db:
        cursor = await db.execute(
            f"SELECT {field} as user_id, COUNT(*) as count FROM verbal_warnings GROUP BY {field} ORDER BY count DESC LIMIT 25"
        )
        rows = await cursor.fetchall()

    return [{"user_id": str(r["user_id"]), "count": r["count"]} for r in rows]


@router.get("/{warning_id}")
async def get_warning(warning_id: int, _user: dict = Depends(get_current_user)):
    async with get_warnings_db() as db:
        cursor = await db.execute(
            "SELECT * FROM verbal_warnings WHERE id = ?", (warning_id,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Warning not found")
    return row_to_dict(row)


@router.put("/{warning_id}")
async def update_warning(
    warning_id: int,
    body: WarningUpdate,
    _user: dict = Depends(get_current_user),
):
    async with get_warnings_db() as db:
        cursor = await db.execute(
            "UPDATE verbal_warnings SET userId=?, reason=?, evidenceLink=?, modId=? WHERE id=?",
            (int(body.userId), body.reason, body.evidenceLink, int(body.modId), warning_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Warning not found")

    async with get_warnings_db() as db:
        cursor = await db.execute(
            "SELECT * FROM verbal_warnings WHERE id = ?", (warning_id,)
        )
        row = await cursor.fetchone()

    return row_to_dict(row)


@router.delete("/{warning_id}")
async def delete_warning(warning_id: int, _user: dict = Depends(get_current_user)):
    async with get_warnings_db() as db:
        cursor = await db.execute(
            "DELETE FROM verbal_warnings WHERE id = ?", (warning_id,)
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Warning not found")

    return {"deleted": True, "id": warning_id}
