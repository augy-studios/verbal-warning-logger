# Polls

The `/poll` command group lets staff create and manage voting polls — typically used for staff evaluations. Polls support anonymous voting, per-user vote limits, and live result viewing.

---

## /poll create

Create a new poll via a modal form.

| Option | Required | Description |
|--------|----------|-------------|
| `channel` | No | Channel to post the poll in (defaults to current channel) |
| `anonymous` | No | Hide voter identities from results (default: false) |
| `max_votes` | No | Maximum number of options each voter can select (0 = unlimited) |

A modal opens where you fill in:

- **Title** — displayed as the embed title
- **Description** — context or instructions shown below the title
- **Options** — each option on its own line (up to 10)

The bot posts the poll as an embed with voting buttons. Users click a button to cast their vote.

---

## /poll edit

Edit an active poll's content.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Poll ID |

Opens a modal to update the title, description, or options. Existing votes are preserved.

---

## /poll delete

Close a poll and disable all voting buttons.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Poll ID |

The poll embed is updated to show it as closed and buttons are disabled. This action cannot be undone.

---

## /poll list

List polls with optional filters.

| Option | Required | Description |
|--------|----------|-------------|
| `filter` | No | `active` (default) or `all` |
| `channel` | No | Filter by channel |
| `user` | No | Filter by creator |

---

## /poll view

View the current live results of a poll.

| Option | Required | Description |
|--------|----------|-------------|
| `id` | Yes | Poll ID |

Returns an embed showing each option with its vote count and a jump link to the original poll message.

For anonymous polls, individual voter identities are hidden; only totals are shown.
