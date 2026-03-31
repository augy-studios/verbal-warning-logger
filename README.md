# Verbal Warning Logger

A Discord moderation bot for logging and managing verbal warnings. Built with discord.py and slash commands, with SQLite storage and no external database required.

## Features

- Log verbal warnings with a reason and evidence link
- Search, paginate, and filter the full warning history
- Edit or delete warnings through Discord modals
- View leaderboards for most-warned users and most-active moderators
- Staff evaluation polls with anonymous voting and reusable templates
- Historical punishment lookup via Auttaja/Supabase integration
- Role hierarchy permission system — no manual per-user grants needed
- All actions logged to a configured channel

## Quick Start

**Requirements:** Python 3.10+

```bash
git clone https://github.com/augy-studios/verbal-warning-logger.git
cd verbal-warning-logger
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
python -m bot.main
```

**.env variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Bot token from the Discord Developer Portal |
| `LOG_CHANNEL_ID` | Yes | Channel ID where warning actions are logged |
| `STAFF_ROLE_ID` | Yes | Minimum role required to use `/verbal` commands |
| `EMBED_COLOR` | No | Embed accent color in hex (default: `0x007FFF`) |
| `SUPABASE_URL` | No | Supabase project URL (Auttaja integration only) |
| `SUPABASE_KEY` | No | Supabase service role key (Auttaja integration only) |

On first run, the bot creates `warnings.db` and `staffpolls.db` and syncs slash commands globally (can take up to 1 hour to propagate).

## Documentation

Full docs are in the [`docs/`](docs/) folder and cover every command group, the permission system, and a step-by-step self-hosting guide.

## License

MIT — © 2026 Augy Studios
