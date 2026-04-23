import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_CLIENT_ID: str = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET: str = os.environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI: str = os.environ["DISCORD_REDIRECT_URI"]
DISCORD_BOT_TOKEN: str = os.environ["DISCORD_BOT_TOKEN"]
DISCORD_GUILD_ID: int = int(os.environ["DISCORD_GUILD_ID"])
STAFF_ROLE_ID: int = int(os.environ["STAFF_ROLE_ID"])

WARNINGS_DB: str = os.environ.get("WARNINGS_DB_PATH", "../warnings.db")
POLLS_DB: str = os.environ.get("POLLS_DB_PATH", "../staffpolls.db")
TEMPLATES_DB: str = os.environ.get("TEMPLATES_DB_PATH", "../polltemplates.db")

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

JWT_SECRET: str = os.environ["JWT_SECRET"]
JWT_EXPIRY_HOURS: int = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))

HOST: str = os.environ.get("HOST", "127.0.0.1")
PORT: int = int(os.environ.get("PORT", "8000"))

DASHBOARD_ORIGIN: str = os.environ.get("DASHBOARD_ORIGIN", "https://dash.vigila.augystudios.com")

LOG_CHANNEL_ID: int = int(os.environ.get("LOG_CHANNEL_ID", "0"))

_embed_color_raw: str = os.environ.get("EMBED_COLOR", "0x007FFF").strip().lower()
EMBED_COLOR: int = int(_embed_color_raw[2:] if _embed_color_raw.startswith("0x") else _embed_color_raw, 16)
