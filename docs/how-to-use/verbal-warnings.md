# Verbal Warnings

The `/verbal` command group is the core of the bot. Use it to record, browse, and manage verbal warnings issued to server members.

---

## /verbal add

Log a new verbal warning.

| Option | Required | Description |
|--------|----------|-------------|
| `user` | Yes | The Discord user being warned |
| `reason` | Yes | What the warning is for |
| `evidence_link` | Yes | A Discord message link as evidence |
| `mod` | No | The moderator issuing the warning (defaults to you) |

The bot responds with a private confirmation embed and posts a full log embed to the configured log channel.

---

## /verbal list

Display all warnings as a paginated embed (10 per page).

Use the **Prev** / **Next** buttons to navigate pages. Press **Close** to dismiss. The view times out after 3 minutes of inactivity.

---

## /verbal search

Filter the warning list to a single user.

| Option | Required | Description |
|--------|----------|-------------|
| `user` | Yes | The Discord user to search for |

Returns a paginated embed of every warning recorded against that user.

---

## /verbal delete

Permanently remove a warning by its ID.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | The numeric warning ID |

> **This action is irreversible.** The deletion is logged to the log channel.

---

## /verbal edit

Edit an existing warning's fields through a modal pop-up.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | The numeric warning ID to edit |

A modal opens with the current values pre-filled. You can update:

- User (Discord ID)
- Moderator (Discord ID)
- Evidence link
- Reason

Changes are logged to the log channel.

---

## /verbal lb

View leaderboards ranked by warning count.

| Option | Required | Description |
|--------|----------|-------------|
| `type` | Yes | `offender` — most-warned users, or `mod` — most-active moderators |

Returns a top-10 embed with user mentions and counts.
