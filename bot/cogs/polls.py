from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from bot.ui import PagedEmbedsView


# ===== DATABASE =====


@dataclass(slots=True)
class StaffPollPoll:
    id: int
    title: str
    description: str
    created_at: str
    created_by: int
    channel_id: int
    message_id: int
    is_active: bool


@dataclass(slots=True)
class StaffPollOption:
    id: int
    poll_id: int
    label: str
    display_order: int


class StaffPollDatabase:
    def __init__(self, path: str = "staffpolls.db") -> None:
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.execute("PRAGMA journal_mode = WAL;")
        await self._conn.execute("PRAGMA synchronous = NORMAL;")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("StaffPollDatabase is not connected")
        return self._conn

    async def init_schema(self) -> None:
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS staffpoll_polls (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                created_by  INTEGER NOT NULL,
                channel_id  INTEGER NOT NULL DEFAULT 0,
                message_id  INTEGER NOT NULL DEFAULT 0,
                is_active   INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS staffpoll_options (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id       INTEGER NOT NULL REFERENCES staffpoll_polls(id) ON DELETE CASCADE,
                label         TEXT    NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS staffpoll_votes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id   INTEGER NOT NULL REFERENCES staffpoll_polls(id) ON DELETE CASCADE,
                option_id INTEGER NOT NULL REFERENCES staffpoll_options(id) ON DELETE CASCADE,
                user_id   INTEGER NOT NULL,
                voted_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(poll_id, user_id)
            )
            """
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ep_active ON staffpoll_polls(is_active)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_eo_poll ON staffpoll_options(poll_id)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ev_poll ON staffpoll_votes(poll_id)"
        )
        await self.conn.commit()

    # ---- polls ----

    async def create_poll(self, title: str, description: str, created_by: int) -> int:
        cur = await self.conn.execute(
            "INSERT INTO staffpoll_polls (title, description, created_by) VALUES (?, ?, ?)",
            (title, description, created_by),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def set_poll_message(self, poll_id: int, channel_id: int, message_id: int) -> None:
        await self.conn.execute(
            "UPDATE staffpoll_polls SET channel_id = ?, message_id = ? WHERE id = ?",
            (channel_id, message_id, poll_id),
        )
        await self.conn.commit()

    async def get_poll(self, poll_id: int) -> Optional[StaffPollPoll]:
        cur = await self.conn.execute(
            "SELECT id, title, description, created_at, created_by, channel_id, message_id, is_active "
            "FROM staffpoll_polls WHERE id = ?",
            (poll_id,),
        )
        return _row_to_poll(await cur.fetchone())

    async def list_polls(
        self,
        active_only: bool = False,
        channel_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> list[StaffPollPoll]:
        conditions: list[str] = []
        params: list[int] = []
        if active_only:
            conditions.append("is_active = 1")
        if channel_id is not None:
            conditions.append("channel_id = ?")
            params.append(channel_id)
        if created_by is not None:
            conditions.append("created_by = ?")
            params.append(created_by)
        sql = (
            "SELECT id, title, description, created_at, created_by, channel_id, message_id, is_active "
            "FROM staffpoll_polls"
        )
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id DESC"
        cur = await self.conn.execute(sql, params)
        return [p for p in (_row_to_poll(r) for r in await cur.fetchall()) if p is not None]

    async def update_poll(self, poll_id: int, title: str, description: str) -> int:
        cur = await self.conn.execute(
            "UPDATE staffpoll_polls SET title = ?, description = ? WHERE id = ?",
            (title, description, poll_id),
        )
        await self.conn.commit()
        return cur.rowcount

    async def disable_poll(self, poll_id: int) -> int:
        cur = await self.conn.execute(
            "UPDATE staffpoll_polls SET is_active = 0 WHERE id = ?", (poll_id,)
        )
        await self.conn.commit()
        return cur.rowcount

    # ---- options ----

    async def add_options(self, poll_id: int, labels: list[str]) -> list[int]:
        ids: list[int] = []
        for order, label in enumerate(labels):
            cur = await self.conn.execute(
                "INSERT INTO staffpoll_options (poll_id, label, display_order) VALUES (?, ?, ?)",
                (poll_id, label, order),
            )
            ids.append(int(cur.lastrowid))
        await self.conn.commit()
        return ids

    async def get_options(self, poll_id: int) -> list[StaffPollOption]:
        cur = await self.conn.execute(
            "SELECT id, poll_id, label, display_order FROM staffpoll_options "
            "WHERE poll_id = ? ORDER BY display_order",
            (poll_id,),
        )
        return [
            StaffPollOption(
                id=int(r["id"]),
                poll_id=int(r["poll_id"]),
                label=str(r["label"]),
                display_order=int(r["display_order"]),
            )
            for r in await cur.fetchall()
        ]

    async def update_option_labels(self, options: list[StaffPollOption], new_labels: list[str]) -> None:
        for option, label in zip(options, new_labels):
            await self.conn.execute(
                "UPDATE staffpoll_options SET label = ? WHERE id = ?", (label, option.id)
            )
        await self.conn.commit()

    # ---- votes ----

    async def cast_vote(self, poll_id: int, option_id: int, user_id: int) -> str:
        """Returns 'new', 'changed', or 'removed'."""
        cur = await self.conn.execute(
            "SELECT id, option_id FROM staffpoll_votes WHERE poll_id = ? AND user_id = ?",
            (poll_id, user_id),
        )
        existing = await cur.fetchone()
        if existing is None:
            await self.conn.execute(
                "INSERT INTO staffpoll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)",
                (poll_id, option_id, user_id),
            )
            await self.conn.commit()
            return "new"
        if int(existing["option_id"]) == option_id:
            await self.conn.execute(
                "DELETE FROM staffpoll_votes WHERE id = ?", (int(existing["id"]),)
            )
            await self.conn.commit()
            return "removed"
        await self.conn.execute(
            "UPDATE staffpoll_votes SET option_id = ?, voted_at = datetime('now') WHERE id = ?",
            (option_id, int(existing["id"])),
        )
        await self.conn.commit()
        return "changed"

    async def get_vote_counts(self, poll_id: int) -> dict[int, int]:
        cur = await self.conn.execute(
            "SELECT option_id, COUNT(*) AS cnt FROM staffpoll_votes WHERE poll_id = ? GROUP BY option_id",
            (poll_id,),
        )
        return {int(r["option_id"]): int(r["cnt"]) for r in await cur.fetchall()}

    async def get_all_votes(self, poll_id: int) -> list[tuple[int, int]]:
        """Returns list of (user_id, option_id) ordered by vote time."""
        cur = await self.conn.execute(
            "SELECT user_id, option_id FROM staffpoll_votes WHERE poll_id = ? ORDER BY voted_at",
            (poll_id,),
        )
        return [(int(r["user_id"]), int(r["option_id"])) for r in await cur.fetchall()]


# ===== HELPERS =====

_CLOSED_COLOR = 0x808080


def _row_to_poll(row: aiosqlite.Row | None) -> Optional[StaffPollPoll]:
    if row is None:
        return None
    return StaffPollPoll(
        id=int(row["id"]),
        title=str(row["title"]),
        description=str(row["description"]),
        created_at=str(row["created_at"]),
        created_by=int(row["created_by"]),
        channel_id=int(row["channel_id"]),
        message_id=int(row["message_id"]),
        is_active=bool(row["is_active"]),
    )


def _parse_options(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _progress_bar(pct: float, length: int = 10) -> str:
    filled = round(pct / 100 * length)
    return "█" * filled + "░" * (length - filled)


async def _resolve_username(client: discord.Client, user_id: int) -> str:
    user = client.get_user(user_id)
    if user is None:
        try:
            user = await client.fetch_user(user_id)
        except discord.NotFound:
            return str(user_id)
    return user.name


def _build_poll_embed(
    poll: StaffPollPoll,
    options: list[StaffPollOption],
    vote_counts: dict[int, int],
    embed_color: int,
    created_by_name: str = "",
    final: bool = False,
) -> discord.Embed:
    total = sum(vote_counts.values())
    color = embed_color if poll.is_active else _CLOSED_COLOR
    status = "Ended" if final else ("Open" if poll.is_active else "Closed")

    embed = discord.Embed(
        title=poll.title,
        color=color,
        description=poll.description if poll.description else None,
    )

    top_count = max(vote_counts.values(), default=0)

    for option in options:
        count = vote_counts.get(option.id, 0)
        pct = (count / total * 100) if total > 0 else 0.0
        bar = _progress_bar(pct)
        is_winner = final and top_count > 0 and count == top_count
        field_name = f"🏆 {option.label}" if is_winner else option.label
        vote_str = f"{count} vote{'s' if count != 1 else ''}"
        if final:
            field_value = f"**{bar} {vote_str} ({pct:.1f}%)**"
        else:
            field_value = f"{bar} **{count}** vote{'s' if count != 1 else ''} ({pct:.1f}%)"
        embed.add_field(name=field_name, value=field_value, inline=False)

    embed.set_footer(
        text=(
            f"Poll #{poll.id} • {status} • "
            f"{total} total vote{'s' if total != 1 else ''} • "
            f"Created by {created_by_name or f'<@{poll.created_by}>'}"
        )
    )
    return embed


# ===== UI =====


async def _send_participants(interaction: discord.Interaction, staffpoll_db: StaffPollDatabase, poll_id: int, embed_color: int) -> None:
    poll = await staffpoll_db.get_poll(poll_id)
    if poll is None:
        await interaction.response.send_message("Poll not found.", ephemeral=True)
        return

    options = await staffpoll_db.get_options(poll_id)
    all_votes = await staffpoll_db.get_all_votes(poll_id)

    by_option: dict[int, list[int]] = {o.id: [] for o in options}
    for user_id, option_id in all_votes:
        if option_id in by_option:
            by_option[option_id].append(user_id)

    total = len(all_votes)
    status = "Open" if poll.is_active else "Closed"
    embed = discord.Embed(
        title=f"Participants — {poll.title}",
        color=embed_color if poll.is_active else _CLOSED_COLOR,
        description=(
            f"**Poll #{poll.id}** • {status} • "
            f"**{total}** participant{'s' if total != 1 else ''}"
        ),
    )

    for option in options:
        voters = by_option.get(option.id, [])
        count = len(voters)
        if voters:
            mentions: list[str] = []
            running = 0
            for uid in voters:
                mention = f"<@{uid}>"
                if running + len(mention) + 2 > 950:
                    mentions.append(f"*…and {count - len(mentions)} more*")
                    break
                mentions.append(mention)
                running += len(mention) + 2
            value = ", ".join(mentions)
        else:
            value = "*No votes yet*"

        embed.add_field(
            name=f"{option.label} ({count} vote{'s' if count != 1 else ''})",
            value=value,
            inline=False,
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


class StaffPollVoteButton(discord.ui.Button["StaffPollVoteView"]):
    def __init__(self, option_id: int, label: str, poll_id: int, is_active: bool) -> None:
        super().__init__(
            label=label[:80],
            style=discord.ButtonStyle.primary if is_active else discord.ButtonStyle.secondary,
            custom_id=f"staffpoll_vote_{poll_id}_{option_id}",
            disabled=not is_active,
        )
        self._option_id = option_id
        self._poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_vote(interaction, self._poll_id, self._option_id)


class StaffPollParticipantsButton(discord.ui.Button["StaffPollVoteView"]):
    def __init__(self, poll_id: int) -> None:
        super().__init__(
            label="Participants",
            style=discord.ButtonStyle.secondary,
            custom_id=f"staffpoll_participants_{poll_id}",
            emoji="📋",
        )
        self._poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await _send_participants(interaction, self.view._staffpoll_db, self._poll_id, self.view._embed_color)


class StaffPollReopenPollButton(discord.ui.Button["StaffPollEndedView"]):
    def __init__(self, poll_id: int) -> None:
        super().__init__(
            label="Reopen Poll",
            style=discord.ButtonStyle.success,
            custom_id=f"staffpoll_reopen_{poll_id}",
            emoji="🔓",
        )
        self._poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_reopen(interaction, self._poll_id)


class StaffPollEndedView(discord.ui.View):
    """Persistent view shown on a poll message after it has been ended."""

    def __init__(
        self,
        poll_id: int,
        options: list[StaffPollOption],
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        created_by: int,
    ) -> None:
        super().__init__(timeout=None)
        self._poll_id = poll_id
        self._options = options
        self._staffpoll_db = staffpoll_db
        self._embed_color = embed_color
        self._created_by = created_by

        self.add_item(StaffPollParticipantsButton(poll_id=poll_id))
        self.add_item(StaffPollReopenPollButton(poll_id=poll_id))

    async def handle_reopen(self, interaction: discord.Interaction, poll_id: int) -> None:
        poll = await self._staffpoll_db.get_poll(poll_id)
        if poll is None:
            await interaction.response.send_message("Poll not found.", ephemeral=True)
            return

        if interaction.user.id != poll.created_by:
            await interaction.response.send_message(
                "Only the poll creator can reopen this poll.", ephemeral=True
            )
            return

        if poll.is_active:
            await interaction.response.send_message(
                "This poll is already open.", ephemeral=True
            )
            return

        await self._staffpoll_db.conn.execute(
            "UPDATE staffpoll_polls SET is_active = 1 WHERE id = ?", (poll_id,)
        )
        await self._staffpoll_db.conn.commit()

        options = await self._staffpoll_db.get_options(poll_id)
        reopened_poll = await self._staffpoll_db.get_poll(poll_id)
        assert reopened_poll is not None

        vote_counts = await self._staffpoll_db.get_vote_counts(poll_id)
        created_by_name = await _resolve_username(interaction.client, poll.created_by)  # type: ignore[arg-type]
        embed = _build_poll_embed(reopened_poll, options, vote_counts, self._embed_color, created_by_name)

        new_view = StaffPollVoteView(
            poll_id=poll_id,
            options=options,
            staffpoll_db=self._staffpoll_db,
            embed_color=self._embed_color,
            is_active=True,
            created_by=poll.created_by,
        )
        interaction.client.add_view(new_view)  # type: ignore[union-attr]
        await interaction.response.edit_message(embed=embed, view=new_view)


class StaffPollEndPollButton(discord.ui.Button["StaffPollVoteView"]):
    def __init__(self, poll_id: int) -> None:
        super().__init__(
            label="End Poll",
            style=discord.ButtonStyle.danger,
            custom_id=f"staffpoll_end_{poll_id}",
            emoji="🔒",
        )
        self._poll_id = poll_id

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_end_poll(interaction, self._poll_id)


class StaffPollVoteView(discord.ui.View):
    """Persistent vote view attached to a staff poll message."""

    def __init__(
        self,
        poll_id: int,
        options: list[StaffPollOption],
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        is_active: bool,
        created_by: int = 0,
    ) -> None:
        super().__init__(timeout=None)
        self._poll_id = poll_id
        self._staffpoll_db = staffpoll_db
        self._embed_color = embed_color
        self._created_by = created_by

        for option in options:
            self.add_item(
                StaffPollVoteButton(
                    option_id=option.id,
                    label=option.label,
                    poll_id=poll_id,
                    is_active=is_active,
                )
            )

        self.add_item(StaffPollParticipantsButton(poll_id=poll_id))
        if is_active:
            self.add_item(StaffPollEndPollButton(poll_id=poll_id))

    async def handle_vote(
        self, interaction: discord.Interaction, poll_id: int, option_id: int
    ) -> None:
        poll = await self._staffpoll_db.get_poll(poll_id)
        if poll is None or not poll.is_active:
            await interaction.response.send_message(
                "This poll is no longer active.", ephemeral=True
            )
            return

        result = await self._staffpoll_db.cast_vote(poll_id, option_id, interaction.user.id)

        options = await self._staffpoll_db.get_options(poll_id)
        opt = next((o for o in options if o.id == option_id), None)
        label = opt.label if opt else "that option"

        vote_counts = await self._staffpoll_db.get_vote_counts(poll_id)
        created_by_name = await _resolve_username(interaction.client, poll.created_by)  # type: ignore[arg-type]
        embed = _build_poll_embed(poll, options, vote_counts, self._embed_color, created_by_name)
        await interaction.response.edit_message(embed=embed)

        if result == "removed":
            confirmation = f"Your vote for **{label}** has been removed."
        elif result == "new":
            confirmation = f"Your vote has been cast for **{label}**."
        else:
            confirmation = f"Your vote has been changed to **{label}**."
        await interaction.followup.send(confirmation, ephemeral=True)

    async def handle_end_poll(self, interaction: discord.Interaction, poll_id: int) -> None:
        poll = await self._staffpoll_db.get_poll(poll_id)
        if poll is None:
            await interaction.response.send_message("Poll not found.", ephemeral=True)
            return

        if interaction.user.id != poll.created_by:
            await interaction.response.send_message(
                "Only the poll creator can end this poll.", ephemeral=True
            )
            return

        if not poll.is_active:
            await interaction.response.send_message(
                "This poll has already ended.", ephemeral=True
            )
            return

        await self._staffpoll_db.disable_poll(poll_id)

        options = await self._staffpoll_db.get_options(poll_id)
        vote_counts = await self._staffpoll_db.get_vote_counts(poll_id)
        ended_poll = await self._staffpoll_db.get_poll(poll_id)
        assert ended_poll is not None

        created_by_name = await _resolve_username(interaction.client, poll.created_by)  # type: ignore[arg-type]
        embed = _build_poll_embed(
            ended_poll, options, vote_counts, self._embed_color, created_by_name, final=True
        )

        ended_view = StaffPollEndedView(
            poll_id=poll_id,
            options=options,
            staffpoll_db=self._staffpoll_db,
            embed_color=self._embed_color,
            created_by=poll.created_by,
        )
        interaction.client.add_view(ended_view)  # type: ignore[union-attr]
        await interaction.response.edit_message(embed=embed, view=ended_view)


# ===== MODALS =====


class CreateStaffPollModal(discord.ui.Modal, title="Create staff poll"):
    poll_title = discord.ui.TextInput(
        label="Poll title",
        placeholder="e.g. Staff Evaluation — April 2026",
        max_length=200,
    )
    poll_description = discord.ui.TextInput(
        label="Description (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="Additional context or instructions for voters.",
        required=False,
        max_length=500,
    )
    poll_options = discord.ui.TextInput(
        label="Options (one per line, minimum 2)",
        style=discord.TextStyle.paragraph,
        placeholder="Promote\nRetain\nDemote",
        max_length=1000,
    )

    def __init__(
        self,
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        target_channel: discord.TextChannel,
    ) -> None:
        super().__init__(timeout=300)
        self._staffpoll_db = staffpoll_db
        self._embed_color = embed_color
        self._target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction) -> None:
        title = self.poll_title.value.strip()
        description = self.poll_description.value.strip() if self.poll_description.value else ""
        options = _parse_options(self.poll_options.value)

        if len(options) < 2:
            await interaction.response.send_message(
                "You must provide at least 2 options, one per line.", ephemeral=True
            )
            return

        if len(options) > 24:
            await interaction.response.send_message(
                "You can have at most 24 options.", ephemeral=True
            )
            return

        if any(len(o) > 80 for o in options):
            await interaction.response.send_message(
                "Each option label must be 80 characters or fewer.", ephemeral=True
            )
            return

        poll_id = await self._staffpoll_db.create_poll(title, description, interaction.user.id)
        await self._staffpoll_db.add_options(poll_id, options)

        poll = await self._staffpoll_db.get_poll(poll_id)
        staffpoll_options = await self._staffpoll_db.get_options(poll_id)

        assert poll is not None
        created_by_name = interaction.user.name
        embed = _build_poll_embed(poll, staffpoll_options, {}, self._embed_color, created_by_name)
        view = StaffPollVoteView(
            poll_id=poll_id,
            options=staffpoll_options,
            staffpoll_db=self._staffpoll_db,
            embed_color=self._embed_color,
            is_active=True,
            created_by=interaction.user.id,
        )

        await interaction.response.defer(ephemeral=True)
        msg = await self._target_channel.send(embed=embed, view=view)
        await self._staffpoll_db.set_poll_message(poll_id, msg.channel.id, msg.id)
        interaction.client.add_view(view)  # type: ignore[union-attr]

        confirm = (
            f"Poll created in {self._target_channel.mention}!"
            if self._target_channel.id != interaction.channel_id
            else "Poll created!"
        )
        await interaction.followup.send(confirm, ephemeral=True)


class EditStaffPollModal(discord.ui.Modal, title="Edit staff poll"):
    def __init__(
        self,
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        poll: StaffPollPoll,
        options: list[StaffPollOption],
    ) -> None:
        super().__init__(timeout=300)
        self._staffpoll_db = staffpoll_db
        self._embed_color = embed_color
        self._poll = poll
        self._options = options

        self.poll_title = discord.ui.TextInput(
            label="Poll title",
            default=poll.title,
            max_length=200,
        )
        self.poll_description = discord.ui.TextInput(
            label="Description (optional)",
            style=discord.TextStyle.paragraph,
            default=poll.description or "",
            required=False,
            max_length=500,
        )
        self.poll_options = discord.ui.TextInput(
            label=f"Options (keep at {len(options)} line{'s' if len(options) != 1 else ''})",
            style=discord.TextStyle.paragraph,
            default="\n".join(o.label for o in options),
            max_length=1000,
        )

        self.add_item(self.poll_title)
        self.add_item(self.poll_description)
        self.add_item(self.poll_options)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        title = self.poll_title.value.strip()
        description = self.poll_description.value.strip() if self.poll_description.value else ""
        new_labels = _parse_options(self.poll_options.value)

        if len(new_labels) != len(self._options):
            await interaction.response.send_message(
                f"Option count must remain {len(self._options)}. "
                "You cannot add or remove options after creation.",
                ephemeral=True,
            )
            return

        if any(len(lbl) > 80 for lbl in new_labels):
            await interaction.response.send_message(
                "Each option label must be 80 characters or fewer.", ephemeral=True
            )
            return

        await self._staffpoll_db.update_poll(self._poll.id, title, description)
        await self._staffpoll_db.update_option_labels(self._options, new_labels)

        poll = await self._staffpoll_db.get_poll(self._poll.id)
        options = await self._staffpoll_db.get_options(self._poll.id)
        vote_counts = await self._staffpoll_db.get_vote_counts(self._poll.id)

        assert poll is not None
        created_by_name = await _resolve_username(interaction.client, poll.created_by)  # type: ignore[arg-type]
        embed = _build_poll_embed(poll, options, vote_counts, self._embed_color, created_by_name)
        new_view = StaffPollVoteView(
            poll_id=self._poll.id,
            options=options,
            staffpoll_db=self._staffpoll_db,
            embed_color=self._embed_color,
            is_active=poll.is_active,
            created_by=poll.created_by,
        )

        updated = False
        if poll.channel_id and poll.message_id:
            channel = interaction.client.get_channel(poll.channel_id)  # type: ignore[union-attr]
            if isinstance(channel, discord.TextChannel):
                try:
                    msg = await channel.fetch_message(poll.message_id)
                    await msg.edit(embed=embed, view=new_view)
                    interaction.client.add_view(new_view)  # type: ignore[union-attr]
                    updated = True
                except discord.NotFound:
                    pass

        note = "Poll updated and message refreshed." if updated else "Poll updated (original message not found)."
        await interaction.response.send_message(note, ephemeral=True)


# ===== COG =====


def _chunk(seq: list, size: int) -> list[list]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


class StaffPollCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        staff_role_id: int,
    ) -> None:
        self.bot = bot
        self.staffpoll_db = staffpoll_db
        self.embed_color = embed_color
        self.staff_role_id = staff_role_id

    async def cog_unload(self) -> None:
        await self.staffpoll_db.close()

    staffpoll = app_commands.Group(name="poll", description="Staff team evaluation polls")

    async def _staff_check(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            raise app_commands.CheckFailure("This command can only be used in a server.")

        member = interaction.user
        if not isinstance(member, discord.Member):
            raise app_commands.CheckFailure("Member context required.")

        if member.guild_permissions.administrator:
            return

        staff_role = interaction.guild.get_role(self.staff_role_id)
        if staff_role is None:
            raise app_commands.CheckFailure("STAFF_ROLE_ID is invalid (role not found).")

        if staff_role in member.roles:
            return

        if any(r.position >= staff_role.position for r in member.roles):
            return

        raise app_commands.CheckFailure("You do not have permission to use this command.")

    # ---- commands ----

    @staffpoll.command(name="create", description="Create a new staff poll")
    @app_commands.describe(channel="Channel to post the poll in (defaults to current channel)")
    async def staffpoll_create(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        await self._staff_check(interaction)
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Please specify a text channel or run this in one.", ephemeral=True
            )
            return
        modal = CreateStaffPollModal(
            staffpoll_db=self.staffpoll_db,
            embed_color=self.embed_color,
            target_channel=target,
        )
        await interaction.response.send_modal(modal)

    @staffpoll.command(name="edit", description="Edit a poll's title, description, or option labels")
    @app_commands.describe(id="ID of the poll to edit")
    async def staffpoll_edit(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        poll = await self.staffpoll_db.get_poll(id)
        if poll is None:
            await interaction.response.send_message(
                f"No poll found with ID `{id}`.", ephemeral=True
            )
            return

        options = await self.staffpoll_db.get_options(id)
        modal = EditStaffPollModal(
            staffpoll_db=self.staffpoll_db,
            embed_color=self.embed_color,
            poll=poll,
            options=options,
        )
        await interaction.response.send_modal(modal)

    @staffpoll.command(name="delete", description="Close and disable a staff poll")
    @app_commands.describe(id="ID of the poll to close")
    async def staffpoll_delete(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        poll = await self.staffpoll_db.get_poll(id)
        if poll is None:
            await interaction.response.send_message(
                f"No poll found with ID `{id}`.", ephemeral=True
            )
            return

        if not poll.is_active:
            await interaction.response.send_message(
                f"Poll `{id}` is already closed.", ephemeral=True
            )
            return

        await self.staffpoll_db.disable_poll(id)

        options = await self.staffpoll_db.get_options(id)
        vote_counts = await self.staffpoll_db.get_vote_counts(id)
        closed_poll = await self.staffpoll_db.get_poll(id)

        assert closed_poll is not None
        created_by_name = await _resolve_username(self.bot, closed_poll.created_by)
        embed = _build_poll_embed(closed_poll, options, vote_counts, self.embed_color, created_by_name)
        closed_view = StaffPollVoteView(
            poll_id=id,
            options=options,
            staffpoll_db=self.staffpoll_db,
            embed_color=self.embed_color,
            is_active=False,
            created_by=poll.created_by,
        )

        updated = False
        if poll.channel_id and poll.message_id:
            channel = self.bot.get_channel(poll.channel_id)
            if isinstance(channel, discord.TextChannel):
                try:
                    msg = await channel.fetch_message(poll.message_id)
                    await msg.edit(embed=embed, view=closed_view)
                    updated = True
                except discord.NotFound:
                    pass

        total = sum(vote_counts.values())
        confirm = discord.Embed(
            title="Poll closed",
            color=self.embed_color,
            description=(
                f"**Poll ID:** `{id}`\n"
                f"**Title:** {poll.title}\n"
                f"**Total votes:** `{total}`\n"
                + ("**Message updated.**" if updated else "**Original message not found.**")
            ),
        )
        await interaction.response.send_message(embed=confirm, ephemeral=True)

    @staffpoll.command(name="list", description="List staff polls")
    @app_commands.describe(
        filter="Show active polls only, or all polls",
        channel="Only show polls posted in this channel",
        user="Only show polls created by this user",
    )
    async def staffpoll_list(
        self,
        interaction: discord.Interaction,
        filter: Literal["active", "all"] = "active",
        channel: Optional[discord.TextChannel] = None,
        user: Optional[discord.Member] = None,
    ) -> None:
        await self._staff_check(interaction)

        polls = await self.staffpoll_db.list_polls(
            active_only=(filter == "active"),
            channel_id=channel.id if channel else None,
            created_by=user.id if user else None,
        )
        if not polls:
            label = "active " if filter == "active" else ""
            await interaction.response.send_message(
                f"No {label}staff polls found.", ephemeral=True
            )
            return

        pages: list[discord.Embed] = []
        total_pages = (len(polls) - 1) // 10 + 1

        filter_parts = [f"`{filter}`"]
        if channel:
            filter_parts.append(f"channel: {channel.mention}")
        if user:
            filter_parts.append(f"creator: {user.mention}")

        for page_index, chunk in enumerate(_chunk(polls, 10), start=1):
            embed = discord.Embed(
                title="Staff polls",
                color=self.embed_color,
                description=(
                    f"**Total:** `{len(polls)}`\n"
                    f"**Filter:** {', '.join(filter_parts)}\n"
                    f"**Page:** `{page_index}/{total_pages}`"
                ),
            )
            for p in chunk:
                status = "Open" if p.is_active else "Closed"
                channel_str = f"<#{p.channel_id}>" if p.channel_id else "Unknown"
                embed.add_field(
                    name=f"#{p.id} — {p.title}",
                    value=(
                        f"**Status:** {status}\n"
                        f"**Channel:** {channel_str}\n"
                        f"**Created:** {p.created_at}\n"
                        f"**By:** <@{p.created_by}>"
                    ),
                    inline=False,
                )
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

    @staffpoll.command(name="view", description="View results and details for a poll")
    @app_commands.describe(id="ID of the poll to view")
    async def staffpoll_view(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        poll = await self.staffpoll_db.get_poll(id)
        if poll is None:
            await interaction.response.send_message(
                f"No poll found with ID `{id}`.", ephemeral=True
            )
            return

        options = await self.staffpoll_db.get_options(id)
        vote_counts = await self.staffpoll_db.get_vote_counts(id)
        created_by_name = await _resolve_username(interaction.client, poll.created_by)  # type: ignore[arg-type]
        embed = _build_poll_embed(poll, options, vote_counts, self.embed_color, created_by_name)

        if poll.channel_id and poll.message_id:
            embed.add_field(
                name="Message",
                value=f"[Jump to poll](https://discord.com/channels/{interaction.guild_id}/{poll.channel_id}/{poll.message_id})",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===== SETUP =====


async def setup(bot: commands.Bot) -> None:
    staffpoll_db = StaffPollDatabase()
    await staffpoll_db.connect()
    await staffpoll_db.init_schema()

    embed_color: int = getattr(bot, "embed_color", 0x007FFF)
    staff_role_id: int = getattr(bot, "staff_role_id", 0)

    cog = StaffPollCog(
        bot=bot,
        staffpoll_db=staffpoll_db,
        embed_color=embed_color,
        staff_role_id=staff_role_id,
    )
    await bot.add_cog(cog)

    # Re-register persistent views for all polls so buttons survive restarts
    all_polls = await staffpoll_db.list_polls(active_only=False)
    for poll in all_polls:
        options = await staffpoll_db.get_options(poll.id)
        if not options:
            continue
        if poll.is_active:
            view: discord.ui.View = StaffPollVoteView(
                poll_id=poll.id,
                options=options,
                staffpoll_db=staffpoll_db,
                embed_color=embed_color,
                is_active=True,
                created_by=poll.created_by,
            )
        else:
            view = StaffPollEndedView(
                poll_id=poll.id,
                options=options,
                staffpoll_db=staffpoll_db,
                embed_color=embed_color,
                created_by=poll.created_by,
            )
        bot.add_view(view)
