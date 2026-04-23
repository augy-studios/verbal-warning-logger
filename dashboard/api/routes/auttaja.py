from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..config import SUPABASE_KEY, SUPABASE_URL

router = APIRouter()

_sb = None


def _get_supabase():
    global _sb
    if _sb is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        try:
            from supabase import create_client
            _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            return None
    return _sb


def _require_supabase():
    sb = _get_supabase()
    if not sb:
        raise HTTPException(
            status_code=503,
            detail="Auttaja integration unavailable — Supabase credentials not configured",
        )
    return sb


class PunishmentUpdate(BaseModel):
    offender: str
    punisher: str
    action: str
    reason: str


@router.get("/offender/{user_id}")
async def offender_history(
    user_id: str,
    show_removed: bool = False,
    _user: dict = Depends(get_current_user),
):
    sb = _require_supabase()
    query = sb.table("punishments").select("*").eq("offender", user_id).order("timestamp", desc=True)
    if not show_removed:
        query = query.eq("deleted", False)
    result = query.execute()
    return {"user_id": user_id, "punishments": result.data}


@router.get("/punisher/{user_id}")
async def punisher_history(
    user_id: str,
    show_removed: bool = False,
    _user: dict = Depends(get_current_user),
):
    sb = _require_supabase()
    query = sb.table("punishments").select("*").eq("punisher", user_id).order("timestamp", desc=True)
    if not show_removed:
        query = query.eq("deleted", False)
    result = query.execute()
    return {"user_id": user_id, "punishments": result.data}


@router.get("/leaderboard")
async def leaderboard(
    mode: str = "offender",
    _user: dict = Depends(get_current_user),
):
    if mode not in ("offender", "punisher"):
        raise HTTPException(status_code=400, detail="mode must be 'offender' or 'punisher'")
    sb = _require_supabase()
    result = sb.table("punishments").select(mode).eq("deleted", False).execute()
    counts: dict[str, int] = {}
    for row in result.data:
        uid = str(row.get(mode, ""))
        if uid:
            counts[uid] = counts.get(uid, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:25]
    return [{"user_id": uid, "count": count} for uid, count in ranked]


@router.get("/{punishment_id}")
async def get_punishment(punishment_id: int, _user: dict = Depends(get_current_user)):
    sb = _require_supabase()
    result = sb.table("punishments").select("*").eq("id", punishment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Punishment not found")
    return result.data[0]


@router.put("/{punishment_id}")
async def update_punishment(
    punishment_id: int,
    body: PunishmentUpdate,
    _user: dict = Depends(get_current_user),
):
    sb = _require_supabase()
    result = sb.table("punishments").update({
        "offender": body.offender,
        "punisher": body.punisher,
        "action": body.action,
        "reason": body.reason,
    }).eq("id", punishment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Punishment not found")
    return result.data[0]
