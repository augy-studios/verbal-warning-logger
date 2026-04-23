from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import (
    DASHBOARD_ORIGIN,
    DISCORD_BOT_TOKEN,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_GUILD_ID,
    DISCORD_REDIRECT_URI,
    JWT_EXPIRY_HOURS,
    JWT_SECRET,
    STAFF_ROLE_ID,
)

DISCORD_API = "https://discord.com/api/v10"
security = HTTPBearer()
router = APIRouter()


def create_token(user_id: str, username: str, avatar: str | None) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "avatar": avatar or "",
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    return decode_token(credentials.credentials)


async def _discord_get(path: str, token: str, bot: bool = False) -> dict:
    headers = {"Authorization": f"Bot {token}" if bot else f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DISCORD_API}{path}", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def check_staff_access(user_id: str) -> bool:
    try:
        member = await _discord_get(
            f"/guilds/{DISCORD_GUILD_ID}/members/{user_id}",
            DISCORD_BOT_TOKEN,
            bot=True,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return False
        raise

    roles = [int(r) for r in member.get("roles", [])]
    if STAFF_ROLE_ID in roles:
        return True

    # Check if any user role is higher than staff role
    try:
        guild_roles = await _discord_get(
            f"/guilds/{DISCORD_GUILD_ID}/roles", DISCORD_BOT_TOKEN, bot=True
        )
    except Exception:
        return False

    staff_pos = next(
        (int(r["position"]) for r in guild_roles if int(r["id"]) == STAFF_ROLE_ID), 0
    )
    user_positions = [
        int(r["position"]) for r in guild_roles if int(r["id"]) in roles
    ]
    return any(p >= staff_pos for p in user_positions)


@router.get("/login")
async def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
    }
    return RedirectResponse(
        f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    )


@router.get("/callback")
async def callback(code: str):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
        )
        if token_resp.status_code != 200:
            return RedirectResponse(f"{DASHBOARD_ORIGIN}/#/login?error=oauth_failed")
        token_data = token_resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(f"{DASHBOARD_ORIGIN}/#/login?error=no_token")

    try:
        user = await _discord_get("/users/@me", access_token)
    except Exception:
        return RedirectResponse(f"{DASHBOARD_ORIGIN}/#/login?error=user_fetch_failed")

    user_id = user["id"]
    has_access = await check_staff_access(user_id)
    if not has_access:
        return RedirectResponse(f"{DASHBOARD_ORIGIN}/#/login?error=no_access")

    jwt_token = create_token(
        user_id=user_id,
        username=user.get("global_name") or user.get("username", "Unknown"),
        avatar=user.get("avatar"),
    )
    return RedirectResponse(f"{DASHBOARD_ORIGIN}/#/dashboard?token={jwt_token}")


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["sub"],
        "username": user["username"],
        "avatar": user.get("avatar"),
        "avatar_url": (
            f"https://cdn.discordapp.com/avatars/{user['sub']}/{user['avatar']}.png"
            if user.get("avatar")
            else f"https://cdn.discordapp.com/embed/avatars/{int(user['sub']) % 5}.png"
        ),
    }


@router.post("/logout")
async def logout():
    return {"message": "Logged out"}
