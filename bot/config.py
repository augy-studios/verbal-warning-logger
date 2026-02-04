from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    token: str
    log_channel_id: int
    staff_role_id: int
    embed_color: int


def _parse_hex_color(value: str) -> int:
    """Accepts values like 0x007FFF or 007FFF."""
    v = value.strip().lower()
    if v.startswith("0x"):
        v = v[2:]
    return int(v, 16)


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing in .env")

    log_channel_id = int(os.getenv("LOG_CHANNEL_ID", "0"))
    staff_role_id = int(os.getenv("STAFF_ROLE_ID", "0"))

    embed_color_raw = os.getenv("EMBED_COLOR", "0x007FFF").strip()
    embed_color = _parse_hex_color(embed_color_raw)

    if log_channel_id <= 0:
        raise RuntimeError("LOG_CHANNEL_ID must be set to a valid channel ID")
    if staff_role_id <= 0:
        raise RuntimeError("STAFF_ROLE_ID must be set to a valid role ID")

    return Settings(
        token=token,
        log_channel_id=log_channel_id,
        staff_role_id=staff_role_id,
        embed_color=embed_color,
    )