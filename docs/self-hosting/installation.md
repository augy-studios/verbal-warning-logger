# Installation

---

## 1. Clone the repository

```bash
git clone https://github.com/augy-studios/verbal-warning-logger.git
cd verbal-warning-logger
```

---

## 2. Create a virtual environment

A virtual environment keeps the bot's dependencies isolated from your system Python.

```bash
python3 -m venv .venv
```

Activate it:

**Linux / macOS:**
```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**
```bat
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

Your prompt should now show `(.venv)` to confirm the environment is active.

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `discord.py >= 2.4.0` | Discord API library |
| `python-dotenv >= 1.0.1` | Load `.env` configuration |
| `aiofiles >= 23.2.1` | Async file I/O |
| `aiosqlite >= 0.20.0` | Async SQLite for warnings and polls |
| `supabase >= 2.0.0` | Auttaja integration (optional) |

---

## 4. Create your .env file

Copy the example file and fill it in:

```bash
cp .env.example .env
```

See the [Configuration](configuration.md) page for details on every variable.

---

## Next step

Once your `.env` is ready, head to [Running the Bot](running.md).
