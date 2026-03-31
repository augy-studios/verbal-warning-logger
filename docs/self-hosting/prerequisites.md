# Prerequisites

Before installing the bot, make sure your system meets the following requirements.

---

## Python

**Python 3.10 or newer is required.** Python 3.11 or 3.12 is recommended for best performance.

Check your version:

```bash
python3 --version
```

If you're on a version older than 3.10, upgrade before continuing. Most package managers (apt, brew, winget) have recent Python versions available.

---

## pip

pip is included with Python. Confirm it's available:

```bash
pip3 --version
```

---

## git

You'll need git to clone the repository:

```bash
git --version
```

Install via your system's package manager if missing (`apt install git`, `brew install git`, etc.).

---

## Operating system

The bot runs on **Linux, macOS, and Windows**. Linux is recommended for production deployments.

---

## Network access

The host machine must be able to reach:

- `discord.com` — for the Discord API and gateway
- `supabase.co` — only if you are using the Auttaja integration

---

## Optional: a process manager

For long-running production deployments, consider a process manager so the bot restarts automatically on crash or reboot:

- **Linux:** `systemd` or `pm2`
- **Windows:** NSSM or Task Scheduler
- **Any platform:** `pm2` (Node-based, works with Python via `--interpreter python3`)
