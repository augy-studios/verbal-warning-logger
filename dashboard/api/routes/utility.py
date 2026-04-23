from fastapi import APIRouter, Depends, HTTPException
import httpx

from ..auth import get_current_user
from ..config import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID
from ..database import get_warnings_db

router = APIRouter()

DISCORD_API = "https://discord.com/api/v10"


async def _bot_get(path: str) -> dict | list:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DISCORD_API}{path}",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
        )
        resp.raise_for_status()
        return resp.json()


@router.get("/ping")
async def ping(_user: dict = Depends(get_current_user)):
    try:
        import time
        start = time.monotonic()
        await _bot_get("/gateway")
        latency = round((time.monotonic() - start) * 1000)
        return {"status": "online", "latency_ms": latency}
    except Exception:
        return {"status": "unknown", "latency_ms": None}


@router.get("/guild")
async def guild_info(_user: dict = Depends(get_current_user)):
    data = await _bot_get(f"/guilds/{DISCORD_GUILD_ID}?with_counts=true")
    return {
        "id": data["id"],
        "name": data["name"],
        "icon": data.get("icon"),
        "member_count": data.get("approximate_member_count"),
        "online_count": data.get("approximate_presence_count"),
    }


@router.get("/discord/user/{user_id}")
async def get_discord_user(user_id: str, _user: dict = Depends(get_current_user)):
    try:
        data = await _bot_get(f"/users/{user_id}")
        avatar_hash = data.get("avatar")
        return {
            "id": data["id"],
            "username": data.get("global_name") or data.get("username", "Unknown User"),
            "discriminator": data.get("discriminator", "0"),
            "avatar_url": (
                f"https://cdn.discordapp.com/avatars/{data['id']}/{avatar_hash}.png"
                if avatar_hash
                else f"https://cdn.discordapp.com/embed/avatars/{int(data['id']) % 5}.png"
            ),
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=502, detail="Discord API error")


@router.get("/channels")
async def get_channels(
    category_id: str | None = None,
    _user: dict = Depends(get_current_user),
):
    channels = await _bot_get(f"/guilds/{DISCORD_GUILD_ID}/channels")
    if category_id:
        channels = [c for c in channels if str(c.get("parent_id")) == category_id]
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "type": c["type"],
            "parent_id": c.get("parent_id"),
            "position": c.get("position", 0),
        }
        for c in sorted(channels, key=lambda x: x.get("position", 0))
    ]


@router.get("/roles")
async def get_roles(_user: dict = Depends(get_current_user)):
    roles = await _bot_get(f"/guilds/{DISCORD_GUILD_ID}/roles")
    return [
        {"id": r["id"], "name": r["name"], "color": r["color"], "position": r["position"]}
        for r in sorted(roles, key=lambda x: x["position"], reverse=True)
        if r["name"] != "@everyone"
    ]


@router.get("/members")
async def get_members(
    role_id: str | None = None,
    query: str | None = None,
    limit: int = 100,
    _user: dict = Depends(get_current_user),
):
    if query:
        data = await _bot_get(
            f"/guilds/{DISCORD_GUILD_ID}/members/search?query={query}&limit={min(limit, 1000)}"
        )
    else:
        data = await _bot_get(
            f"/guilds/{DISCORD_GUILD_ID}/members?limit={min(limit, 1000)}"
        )

    members = []
    for m in data:
        u = m.get("user", {})
        if role_id and role_id not in m.get("roles", []):
            continue
        avatar_hash = u.get("avatar")
        members.append({
            "id": u.get("id"),
            "username": m.get("nick") or u.get("global_name") or u.get("username", "Unknown"),
            "roles": m.get("roles", []),
            "avatar_url": (
                f"https://cdn.discordapp.com/avatars/{u['id']}/{avatar_hash}.png"
                if avatar_hash and u.get("id")
                else None
            ),
        })
    return members


@router.get("/warning-ids")
async def get_warning_ids(
    mode: str = "offender",
    _user: dict = Depends(get_current_user),
):
    if mode not in ("offender", "mod"):
        raise HTTPException(status_code=400, detail="mode must be 'offender' or 'mod'")
    field = "userId" if mode == "offender" else "modId"
    async with get_warnings_db() as db:
        cursor = await db.execute(
            f"SELECT DISTINCT {field} as user_id, COUNT(*) as count FROM verbal_warnings GROUP BY {field} ORDER BY count DESC"
        )
        rows = await cursor.fetchall()
    return [{"user_id": str(r["user_id"]), "count": r["count"]} for r in rows]
