# Auttaja History

The `/auttaja` command group provides read (and limited write) access to historical punishment records previously managed by the Auttaja bot. This data lives in a Supabase table and requires additional configuration — see [Configuration](../self-hosting/configuration.md#auttaja--supabase).

> If Supabase is not configured, all `/auttaja` commands will be unavailable.

---

## /auttaja offender

View all punishments received by a user.

| Option | Required | Description |
|--------|----------|-------------|
| `user` | Yes | The Discord user to look up |
| `show_removed` | No | Include punishments that were removed/reversed (default: false) |

Returns a paginated embed sorted by timestamp. Each entry shows the action type, reason, punisher, and timestamp.

**Action types and their indicators:**

| Action | Indicator |
|--------|-----------|
| ban | 🔨 |
| tempban | 🕐 |
| softban | 🪃 |
| mute | 🔇 |
| kick | 👢 |
| warn | ⚠️ |

---

## /auttaja punisher

View all punishments issued by a staff member.

| Option | Required | Description |
|--------|----------|-------------|
| `user` | Yes | The staff member to look up |
| `show_removed` | No | Include removed punishments (default: false) |

---

## /auttaja lb

Leaderboard from the Auttaja historical records.

| Option | Required | Description |
|--------|----------|-------------|
| `type` | Yes | `offender` — most-punished users, or `punisher` — most-active staff |

---

## /auttaja edit

Edit a punishment record via a modal.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | The Supabase punishment record ID |

A modal opens with editable fields:

- Offender (Discord ID)
- Punisher (Discord ID)
- Action type
- Reason
