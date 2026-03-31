# Running the Bot

---

## Starting the bot

With your virtual environment active and `.env` configured:

```bash
python -m bot.main
```

On a successful start you should see console output like:

```
Logged in as Verbal Warning Logger#1234 (ID: 123456789012345678)
```

---

## First-run behavior

On the very first run, the bot automatically:

- Creates `warnings.db` — SQLite database for verbal warnings
- Creates `staffpolls.db` — SQLite database for polls and templates
- Initializes all table schemas
- Syncs slash commands globally with Discord

> **Global command sync can take up to an hour** to propagate to all servers. Commands will appear in your server once Discord's cache updates.

---

## Faster command sync during development

To make slash commands appear immediately in a single server (useful while testing), edit `bot/main.py` and replace the sync line in `setup_hook`:

```python
# Replace this:
await self.tree.sync()

# With this (substituting your server's ID):
await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
```

Commands will appear in that guild within seconds. Remember to revert this change before deploying to production if you want the bot to work in multiple servers.

---

## Keeping the bot running

For a production deployment you should run the bot as a background service so it survives terminal disconnects and server reboots.

### systemd (Linux)

Create `/etc/systemd/system/verbal-warning-logger.service`:

```ini
[Unit]
Description=Verbal Warning Logger Discord Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/verbal-warning-logger
ExecStart=/path/to/verbal-warning-logger/.venv/bin/python -m bot.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable verbal-warning-logger
sudo systemctl start verbal-warning-logger
```

Check logs with:

```bash
sudo journalctl -u verbal-warning-logger -f
```

### pm2 (any platform)

```bash
pm2 start "python -m bot.main" --name verbal-warning-logger --interpreter python3
pm2 save
pm2 startup
```

---

## Stopping the bot

Send `Ctrl+C` in the terminal, or if running as a service:

```bash
sudo systemctl stop verbal-warning-logger
# or
pm2 stop verbal-warning-logger
```

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `KeyError: DISCORD_TOKEN` | `.env` file is missing or not in the project root |
| Commands not appearing | Global sync is still propagating — wait up to 1 hour, or use guild sync |
| `/auttaja` commands missing | `SUPABASE_URL` / `SUPABASE_KEY` are not set |
| `discord.errors.Forbidden` | Bot is missing required permissions in the channel or server |
| Permission errors on `/verbal` | The user's highest role is below `STAFF_ROLE_ID` in the role list |
