# Verbal Warning Logger

**Verbal Warning Logger** is a Discord moderation bot built with discord.py that helps server staff track, search, and manage verbal warnings issued to users. Everything is stored locally in SQLite — no external database required for core functionality.

## What it does

- **Log verbal warnings** with a reason, evidence link, and the moderator responsible
- **Search and paginate** the full warning history, filtered by user
- **Edit or delete** individual warnings through a clean modal interface
- **View leaderboards** of most-warned users or most-active moderators
- **Import historical punishments** from the Auttaja bot via Supabase
- **Run staff evaluation polls** with anonymous voting, vote limits, and reusable templates
- **Retrieve IDs** for channels, roles, and users in bulk

## Navigation

| Section | Description |
|---------|-------------|
| [How to Use](how-to-use/README.md) | Command-by-command guide for moderators and staff |
| [Self-Hosting](self-hosting/README.md) | How to deploy your own instance |
| [Command Reference](reference/commands.md) | Quick-reference table of every command |
| [Database Schema](reference/database-schema.md) | Table definitions for both SQLite databases |

## License

MIT — © 2026 Augy Studios
