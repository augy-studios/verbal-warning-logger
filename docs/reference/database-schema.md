# Database Schema

The bot uses two local SQLite files that are created automatically on first run.

---

## warnings.db

Stores all verbal warning records.

### verbal_warnings

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | Unique warning ID |
| `createdAt` | TEXT | Timestamp (UTC, auto-set on insert) |
| `userId` | INTEGER | Discord user ID of the person warned |
| `reason` | TEXT | Reason for the warning |
| `evidenceLink` | TEXT | Discord message link used as evidence |
| `modId` | INTEGER | Discord user ID of the moderating staff member |

**Index:** `idx_vw_userId` on `userId` for fast user-based lookups.

```sql
CREATE TABLE verbal_warnings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    createdAt    TEXT    NOT NULL DEFAULT (datetime('now')),
    userId       INTEGER NOT NULL,
    reason       TEXT    NOT NULL,
    evidenceLink TEXT    NOT NULL,
    modId        INTEGER NOT NULL
);

CREATE INDEX idx_vw_userId ON verbal_warnings (userId);
```

---

## staffpolls.db

Stores polls, their options, and voter records.

### staffpoll_polls

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique poll ID |
| `title` | TEXT | Poll title |
| `description` | TEXT | Poll description (default: empty) |
| `created_at` | TEXT | Creation timestamp (UTC) |
| `created_by` | INTEGER | Discord user ID of creator |
| `channel_id` | INTEGER | Channel where the poll was posted |
| `message_id` | INTEGER | Message ID of the poll embed |
| `is_active` | INTEGER | 1 = open, 0 = closed |
| `is_anonymous` | INTEGER | 1 = voter identities hidden |
| `max_votes` | INTEGER | Max options per voter (0 = unlimited) |

### staffpoll_options

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Unique option ID |
| `poll_id` | INTEGER FK | References `staffpoll_polls.id` (CASCADE DELETE) |
| `label` | TEXT | Option text shown on the button |
| `display_order` | INTEGER | Ordering of buttons (ascending) |

---

## Supabase (Auttaja integration)

The Auttaja cog reads from and writes to an external Supabase table. This is not managed by the bot — it is assumed to already exist from a prior Auttaja deployment.

### public.punishments

| Column | Description |
|--------|-------------|
| `id` | Record ID |
| `guild_id` | Discord server ID |
| `offender` | Discord user ID of the punished member |
| `punisher` | Discord user ID of the staff member |
| `reason` | Reason for the punishment |
| `action` | Action type: `ban`, `tempban`, `softban`, `mute`, `kick`, `warn` |
| `timestamp` | When the punishment was issued |
| `duration` | Duration (for tempbans/mutes) |
| `deleted` | Soft-delete flag |
| `removed_by` | Who removed the punishment |
| `removed_reason` | Why the punishment was removed |
| `resolve` | Resolution notes |
