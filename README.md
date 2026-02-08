# Verbal Warning Logger

A modern **Discord.py slash‑command moderation bot** for tracking and managing **verbal warnings** with a clean UI, pagination, and SQLite database storage.

---

## ✨ Features

### Moderation (Staff‑only)

* `/verbal add` — Add a verbal warning with evidence link
* `/verbal list` — View all warnings (paginated)
* `/verbal search <user>` — View warnings for a specific user
* `/verbal delete <id>` — Delete a warning by ID
* `/verbal edit <id>` — Edit a warning using a modal UI
* `/verbal lb <offender|mod>` — Leaderboard (most warned users / most active moderators)

### Utility

* `/ping` — Bot latency
* `/about` — Bot info
* `/retrieveids channels` — Get channel IDs in a category
* `/retrieveids users` — Get user IDs from a role
* `/retrieveids leaderboard` — Get user IDs from DB (mods/offenders)

### Core System

* SQLite database (no external DB required)
* Slash‑command based (modern Discord UI)
* Paginated embeds with buttons
* Staff‑role hierarchy permission system
* Automatic logging to a log channel
* Modal UI for editing warnings

---

## 🗄 Database

SQLite file: `warnings.db`

Table: `verbal_warnings`

| Column       | Type    | Description                  |
| ------------ | ------- | ---------------------------- |
| id           | INTEGER | Primary key                  |
| createdAt    | TEXT    | Timestamp                    |
| userId       | INTEGER | Warned user                  |
| reason       | TEXT    | Warning reason               |
| evidenceLink | TEXT    | Discord message link         |
| modId        | INTEGER | Moderator who issued warning |

The database is automatically created on first run.

---

## 🔐 Permissions

All `/verbal` commands require:

* Server Administrator **OR**
* Staff role (`STAFF_ROLE_ID`) **OR**
* Any role higher than the staff role

Utility commands have their own permission requirements where applicable.

---

## 📦 Requirements

* Python **3.10+** (3.11/3.12 recommended)
* Linux / Windows / macOS
* Discord bot token

Python packages:

* discord.py
* aiosqlite
* python-dotenv

(Installed automatically via `requirements.txt`)

---

## ⚙️ Installation

### 1. Create Discord Bot

1. Go to Discord Developer Portal
2. Create Application → Add Bot
3. Copy Bot Token
4. Invite bot with scopes:

   * `bot`
   * `applications.commands`

**No privileged intents required**

---

### 2. Install Bot

```bash
git clone <your-repo-url>
cd verbal-warning-logger

python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

---

### 3. Configure Environment

Create `.env` file:

```env
DISCORD_TOKEN=YOUR_BOT_TOKEN
LOG_CHANNEL_ID=123456789012345678
STAFF_ROLE_ID=123456789012345678
EMBED_COLOR=0x007FFF
```

**Descriptions**

* `DISCORD_TOKEN` — Bot token from Discord
* `LOG_CHANNEL_ID` — Channel where all warning actions are logged
* `STAFF_ROLE_ID` — Minimum role required to use `/verbal` commands
* `EMBED_COLOR` — Embed color in HEX

---

### 4. Run Bot

```bash
python -m bot.main
```

On first run the bot will:

* Create `warnings.db`
* Create database tables
* Sync slash commands

---

## 🧪 Development Tips

### Faster Command Sync (Guild‑only)

Global sync can take several minutes. For faster development, edit `bot/main.py`:

Replace:

```python
await self.tree.sync()
```

With:

```python
await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
```

---

## 📁 Project Structure

```
bot/
 ├── main.py
 ├── config.py
 ├── db.py
 ├── checks.py
 ├── utility.py
 ├── verbal.py
 ├── ui.py
 └── ...

warnings.db
README.md
requirements.txt
.env
```

---

## 🧩 How It Works

* Slash commands handled via **discord.app_commands**
* Database powered by **aiosqlite (async SQLite)**
* Pagination UI built using **discord.ui.View**
* Permission system based on role hierarchy
* Logging automatically sent to configured channel

---

## 🛠 Troubleshooting

### Commands not appearing

* Wait for global sync (can take up to 1 hour)
* Or use guild‑only sync during development

### "Database not connected"

* Ensure bot started successfully
* Check console for errors

### Permission denied

* Verify `STAFF_ROLE_ID`
* Ensure role hierarchy is correct

---

## 📜 License

[MIT License](./LICENSE)

---

## 👤 Author

Created by **Augy**

Contact: [augy@augystudios.com](mailto:augy@augystudios.com)
