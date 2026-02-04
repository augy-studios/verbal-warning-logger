# Verbal Warning Logger

A small **Discord.py slash-command bot** for tracking **verbal warnings**.

## Features

- `/verbal add` — add a verbal warning
- `/verbal list` — list all warnings (paginated embeds)
- `/verbal search` — list warnings for a user (paginated embeds)
- `/verbal delete` — delete by warning ID
- `/verbal edit` — edit by warning ID (modal)
- `/ping` — show bot latency
- `/about` — owner + contact info

## Database

SQLite table: `verbal_warnings`

Columns:
- `id` (INTEGER, PK, AUTOINCREMENT)
- `createdAt` (TEXT, default `datetime('now')`)
- `userId` (INTEGER)
- `reason` (TEXT)
- `evidenceLink` (TEXT)
- `modId` (INTEGER)

## Permissions

All `/verbal ...` commands are restricted to:
- members with the **Staff role** (`STAFF_ROLE_ID`) **OR**
- members with any role **higher than** that staff role, **OR**
- server administrators.

## Setup (Linux Debian)

### 1) Create a bot in Discord Developer Portal
- Create an application, add a bot.
- Enable the necessary intents (no privileged intents are required).
- Invite it to your server with the **applications.commands** scope and bot scope.

### 2) Install

```bash
git clone <your repo url>
cd verbal-warning-logger
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in:
- `DISCORD_TOKEN`
- `LOG_CHANNEL_ID`
- `STAFF_ROLE_ID`
- `EMBED_COLOR`

### 4) Run

```bash
python -m main
```

## Development notes

- Slash commands are synced globally by default. Global sync can take time.
If you want faster iteration, you can change `await self.tree.sync()` in `main.py`
to guild-only sync:

### Example:

```bash
await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
```
