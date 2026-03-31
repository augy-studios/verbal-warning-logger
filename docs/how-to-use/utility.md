# Utility Commands

These commands help with server administration tasks like bulk ID retrieval and bot diagnostics.

---

## /ping

Check the bot's current gateway latency. Response is visible only to you.

---

## /about

Display bot version information, author details, and a short description.

---

## /help

Open the interactive help menu. A set of category buttons lets you browse command documentation without leaving Discord.

Categories available in the help menu:

- Verbal Warnings
- Auttaja
- Utility
- Polls
- Poll Templates

---

## /retrieveids channels

Get a list of all channel IDs inside a category.

| Option | Required | Description |
|--------|----------|-------------|
| `category` | Yes | The category channel to scan |

Returns a formatted list of `channel-name: ID` pairs. Useful for bulk configuration or scripting.

> Requires the **Manage Channels** permission.

---

## /retrieveids users

Get a list of all member IDs that have a specific role.

| Option | Required | Description |
|--------|----------|-------------|
| `role` | Yes | The role to scan |

Returns a list of `username: ID` pairs for every member with that role.

> Requires the **Manage Roles** permission.

---

## /retrieveids leaderboard

Get the user IDs of the top entries from the verbal warnings leaderboard.

| Option | Required | Description |
|--------|----------|-------------|
| `type` | Yes | `offender` or `mod` |

Returns raw Discord user IDs in order of ranking.

---

## /retrieveids searchusers

Search server members by username or display name.

| Option | Required | Description |
|--------|----------|-------------|
| `text` | Yes | The search string |

Returns a list of matching members with their IDs.
