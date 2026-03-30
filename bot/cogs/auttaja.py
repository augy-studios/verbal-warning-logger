from __future__ import annotations

import datetime
from collections import Counter
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from supabase import AsyncClient, acreate_client

from bot.ui import PagedEmbedsView


# ===== DATA CLASSES =====


class AuttajaPunishment:
    """Mirrors the `public.punishments` Supabase table."""

    __slots__ = (
        "id",
        "guild_id",
        "offender",
        "punisher",
        "reason",
        "action",
        "timestamp",
        "duration",
        "deleted",
        "removed_by",
        "removed_reason",
        "resolve",
    )

    def __init__(self, row: dict) -> None:
        self.id: str = str(row.get("id", ""))
        self.guild_id: str = str(row.get("guild_id", ""))
        self.offender: str = str(row.get("offender", ""))
        self.punisher: str = str(row.get("punisher", ""))
        self.reason: str = row.get("reason") or ""
        self.action: str = row.get("action") or "unknown"
        self.duration: str = str(row.get("duration") or "0")
        self.deleted: bool | None = row.get("deleted")
        self.removed_by: str | None = row.get("removed_by")
        self.removed_reason: str | None = row.get("removed_reason")
        self.resolve: str | None = row.get("resolve")

        # timestamp is stored as epoch_time float in Supabase (or as ISO string)
        raw_ts = row.get("timestamp")
        if isinstance(raw_ts, (int, float)):
            self.timestamp = datetime.datetime.fromtimestamp(raw_ts, tz=datetime.timezone.utc)
        elif isinstance(raw_ts, str):
            try:
                self.timestamp = datetime.datetime.fromisoformat(raw_ts)
            except ValueError:
                self.timestamp = None  # type: ignore[assignment]
        elif isinstance(raw_ts, dict) and "epoch_time" in raw_ts:
            # RethinkDB-style export artefact that survived into Supabase
            self.timestamp = datetime.datetime.fromtimestamp(
                raw_ts["epoch_time"], tz=datetime.timezone.utc
            )
        else:
            self.timestamp = None  # type: ignore[assignment]

    @property
    def ts_str(self) -> str:
        if self.timestamp:
            return self.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        return "Unknown date"

    @property
    def duration_str(self) -> str:
        try:
            secs = int(self.duration)
        except (ValueError, TypeError):
            return self.duration or "—"
        if secs == 0:
            return "Permanent"
        hours, remainder = divmod(secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds:
            parts.append(f"{seconds}s")
        return " ".join(parts) if parts else "0s"


# ===== SUPABASE CLIENT =====


class AuttajaDB:
    """Thin async wrapper around the Supabase `punishments` table."""

    TABLE = "punishments"
    SCHEMA = "public"

    def __init__(self, url: str, key: str) -> None:
        self._url = url
        self._key = key
        self._client: AsyncClient | None = None

    async def connect(self) -> None:
        self._client = await acreate_client(self._url, self._key)

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError("AuttajaDB.connect() has not been called yet.")
        return self._client

    async def search_by_offender(self, user_id: str) -> list[AuttajaPunishment]:
        response = (
            await self.client.table(self.TABLE)
            .select("*")
            .eq("offender", user_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return [AuttajaPunishment(row) for row in (response.data or [])]

    async def search_by_punisher(self, user_id: str) -> list[AuttajaPunishment]:
        response = (
            await self.client.table(self.TABLE)
            .select("*")
            .eq("punisher", user_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return [AuttajaPunishment(row) for row in (response.data or [])]

    async def leaderboard_offenders(self) -> list[tuple[str, int]]:
        """Returns (user_id, count) sorted descending."""
        response = (
            await self.client.table(self.TABLE)
            .select("offender")
            .execute()
        )
        counts: Counter[str] = Counter(row["offender"] for row in (response.data or []))
        return counts.most_common()

    async def leaderboard_punishers(self) -> list[tuple[str, int]]:
        """Returns (user_id, count) sorted descending."""
        response = (
            await self.client.table(self.TABLE)
            .select("punisher")
            .execute()
        )
        counts: Counter[str] = Counter(row["punisher"] for row in (response.data or []))
        return counts.most_common()

    async def get_punishment(self, punishment_id: str) -> AuttajaPunishment | None:
        response = (
            await self.client.table(self.TABLE)
            .select("*")
            .eq("id", punishment_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return AuttajaPunishment(rows[0]) if rows else None

    async def update_punishment(
        self,
        punishment_id: str,
        offender: str,
        punisher: str,
        reason: str,
        action: str,
    ) -> int:
        response = (
            await self.client.table(self.TABLE)
            .update({
                "offender": offender,
                "punisher": punisher,
                "reason": reason,
                "action": action,
            })
            .eq("id", punishment_id)
            .execute()
        )
        return len(response.data or [])

    async def action_breakdown(self, user_id: str, role: Literal["offender", "punisher"]) -> dict[str, int]:
        """Returns {action: count} for a given user in a given role."""
        response = (
            await self.client.table(self.TABLE)
            .select("action")
            .eq(role, user_id)
            .execute()
        )
        counts: Counter[str] = Counter(row["action"] for row in (response.data or []))
        return dict(counts)


# ===== HELPERS =====

ACTION_EMOJIS: dict[str, str] = {
    "ban": "🔨",
    "mute": "🔇",
    "kick": "👢",
    "warn": "⚠️",
    "softban": "🪃",
    "tempban": "⏳",
}


def _action_emoji(action: str) -> str:
    return ACTION_EMOJIS.get(action.lower(), "📋")


def _mention(user_id: str | int) -> str:
    return f"<@{user_id}>"


def _chunk(seq: list, size: int) -> list[list]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def _parse_user_arg(raw: str) -> str | None:
    """Accept a raw string that is either a mention (<@123>) or a bare user ID."""
    raw = raw.strip().lstrip("<@").rstrip(">").strip("!")
    if raw.isdigit():
        return raw
    return None


def _build_punishment_field(p: AuttajaPunishment, show_offender: bool = False) -> tuple[str, str]:
    emoji = _action_emoji(p.action)
    name = f"{emoji} `{p.action.upper()}` • ID `{p.id}` • {p.ts_str}"
    lines = []
    if show_offender:
        lines.append(f"**Offender:** {_mention(p.offender)} (`{p.offender}`)")
    else:
        lines.append(f"**Punisher:** {_mention(p.punisher)} (`{p.punisher}`)")
    if p.reason:
        reason_preview = p.reason[:300] + ("…" if len(p.reason) > 300 else "")
        lines.append(f"**Reason:** {reason_preview}")
    if p.duration and p.action.lower() in ("mute", "tempban"):
        lines.append(f"**Duration:** {p.duration_str}")
    if p.deleted:
        lines.append(f"🗑️ **Removed by:** {_mention(p.removed_by)} — _{p.removed_reason}_")
    return name, "\n".join(lines)


def _build_action_summary(breakdown: dict[str, int]) -> str:
    if not breakdown:
        return "No actions."
    return "  ".join(
        f"{_action_emoji(act)} **{act.upper()}**: `{cnt}`"
        for act, cnt in sorted(breakdown.items(), key=lambda x: -x[1])
    )


# ===== EDIT MODAL =====


class EditAuttajaModal(discord.ui.Modal, title="Edit Auttaja punishment"):
    def __init__(
        self,
        auttaja_db: AuttajaDB,
        punishment: AuttajaPunishment,
        embed_color: int,
        log_channel_id: int,
    ) -> None:
        super().__init__(timeout=300)
        self.auttaja_db = auttaja_db
        self.punishment = punishment
        self.embed_color = embed_color
        self.log_channel_id = log_channel_id

        self.offender_id = discord.ui.TextInput(
            label="Offender ID",
            placeholder="e.g. 123456789012345678",
            default=str(punishment.offender),
            max_length=25,
        )
        self.punisher_id = discord.ui.TextInput(
            label="Punisher ID",
            placeholder="e.g. 123456789012345678",
            default=str(punishment.punisher),
            max_length=25,
        )
        self.action = discord.ui.TextInput(
            label="Action",
            placeholder="ban, mute, kick, warn, softban, tempban",
            default=punishment.action,
            max_length=20,
        )
        self.reason = discord.ui.TextInput(
            label="Reason",
            style=discord.TextStyle.paragraph,
            default=punishment.reason,
            max_length=1000,
        )

        self.add_item(self.offender_id)
        self.add_item(self.punisher_id)
        self.add_item(self.action)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        offender = self.offender_id.value.strip()
        punisher = self.punisher_id.value.strip()
        action = self.action.value.strip().lower()
        reason = self.reason.value.strip()

        if not offender.isdigit() or not punisher.isdigit():
            await interaction.response.send_message(
                "Offender ID and Punisher ID must be numbers.", ephemeral=True
            )
            return

        if not action:
            await interaction.response.send_message("Action cannot be empty.", ephemeral=True)
            return

        if not reason:
            await interaction.response.send_message("Reason cannot be empty.", ephemeral=True)
            return

        changed = await self.auttaja_db.update_punishment(
            punishment_id=self.punishment.id,
            offender=offender,
            punisher=punisher,
            reason=reason,
            action=action,
        )

        if changed <= 0:
            await interaction.response.send_message("Nothing was updated (ID not found).", ephemeral=True)
            return

        embed = discord.Embed(
            title="Auttaja punishment updated",
            color=self.embed_color,
            description=(
                f"**ID:** `{self.punishment.id}`\n"
                f"**Offender:** {_mention(offender)} (`{offender}`)\n"
                f"**Punisher:** {_mention(punisher)} (`{punisher}`)\n"
                f"**Action:** `{action.upper()}`\n"
                f"**Reason:** {reason}"
            ),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        if interaction.client and isinstance(interaction.client, commands.Bot):
            channel = interaction.client.get_channel(self.log_channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)


# ===== COG =====


class AuttajaCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        auttaja_db: AuttajaDB,
        embed_color: int,
        log_channel_id: int,
        staff_role_id: int,
    ) -> None:
        self.bot = bot
        self.auttaja_db = auttaja_db
        self.embed_color = embed_color
        self.log_channel_id = log_channel_id
        self.staff_role_id = staff_role_id

    auttaja = app_commands.Group(name="auttaja", description="Browse historical Auttaja bot punishments")

    # ---- permission check ----

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

    # ---- /auttaja search offender ----

    @auttaja.command(
        name="offender",
        description="Show all Auttaja punishments received by a user",
    )
    @app_commands.describe(
        user="User mention or user ID",
        show_removed="Include removed/deleted punishments in the results (default: False)",
    )
    async def auttaja_offender(
        self,
        interaction: discord.Interaction,
        user: str,
        show_removed: bool = False,
    ) -> None:
        await self._staff_check(interaction)

        user_id = _parse_user_arg(user)
        if user_id is None:
            await interaction.response.send_message(
                "Please provide a valid user mention or user ID.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        all_punishments = await self.auttaja_db.search_by_offender(user_id)
        punishments = all_punishments if show_removed else [p for p in all_punishments if not p.deleted]
        breakdown = await self.auttaja_db.action_breakdown(user_id, "offender")

        if not punishments:
            msg = f"No Auttaja punishments found for {_mention(user_id)} (`{user_id}`)."
            if not show_removed and any(p.deleted for p in all_punishments):
                msg += " (There are removed punishments — use `show_removed: True` to include them.)"
            await interaction.followup.send(msg, ephemeral=True)
            return

        total = len(punishments)
        page_count = (total - 1) // 5 + 1
        removed_note = " *(including removed)*" if show_removed else ""
        pages: list[discord.Embed] = []

        for page_index, chunk in enumerate(_chunk(punishments, 5), start=1):
            embed = discord.Embed(
                title="Auttaja Punishments — Offender",
                color=self.embed_color,
                description=(
                    f"**User:** {_mention(user_id)} (`{user_id}`)\n"
                    f"**Total punishments:** `{total}`{removed_note}\n"
                    f"**Breakdown:** {_build_action_summary(breakdown)}\n"
                    f"**Page:** `{page_index}/{page_count}`"
                ),
            )
            for p in chunk:
                field_name, field_value = _build_punishment_field(p, show_offender=False)
                embed.add_field(name=field_name, value=field_value, inline=False)
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.followup.send(embed=pages[0], view=view)

    # ---- /auttaja punisher ----

    @auttaja.command(
        name="punisher",
        description="Show all Auttaja punishments issued by a staff member",
    )
    @app_commands.describe(
        user="User mention or user ID",
        show_removed="Include removed/deleted punishments in the results (default: False)",
    )
    async def auttaja_punisher(
        self,
        interaction: discord.Interaction,
        user: str,
        show_removed: bool = False,
    ) -> None:
        await self._staff_check(interaction)

        user_id = _parse_user_arg(user)
        if user_id is None:
            await interaction.response.send_message(
                "Please provide a valid user mention or user ID.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        all_punishments = await self.auttaja_db.search_by_punisher(user_id)
        punishments = all_punishments if show_removed else [p for p in all_punishments if not p.deleted]
        breakdown = await self.auttaja_db.action_breakdown(user_id, "punisher")

        if not punishments:
            msg = f"No Auttaja punishments issued by {_mention(user_id)} (`{user_id}`)."
            if not show_removed and any(p.deleted for p in all_punishments):
                msg += " (There are removed punishments — use `show_removed: True` to include them.)"
            await interaction.followup.send(msg, ephemeral=True)
            return

        total = len(punishments)
        page_count = (total - 1) // 5 + 1
        removed_note = " *(including removed)*" if show_removed else ""
        pages: list[discord.Embed] = []

        for page_index, chunk in enumerate(_chunk(punishments, 5), start=1):
            embed = discord.Embed(
                title="Auttaja Punishments — Punisher",
                color=self.embed_color,
                description=(
                    f"**Punisher:** {_mention(user_id)} (`{user_id}`)\n"
                    f"**Total punishments issued:** `{total}`{removed_note}\n"
                    f"**Breakdown:** {_build_action_summary(breakdown)}\n"
                    f"**Page:** `{page_index}/{page_count}`"
                ),
            )
            for p in chunk:
                field_name, field_value = _build_punishment_field(p, show_offender=True)
                embed.add_field(name=field_name, value=field_value, inline=False)
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.followup.send(embed=pages[0], view=view)

    # ---- /auttaja lb ----

    @auttaja.command(
        name="lb",
        description="Auttaja punishment leaderboard",
    )
    @app_commands.describe(
        mode="offender = most punished users, punisher = most active punishers"
    )
    async def auttaja_lb(
        self,
        interaction: discord.Interaction,
        mode: Literal["offender", "punisher"],
    ) -> None:
        await self._staff_check(interaction)

        await interaction.response.defer(ephemeral=False)

        if mode == "offender":
            ranked = await self.auttaja_db.leaderboard_offenders()
            title = "🏆 Auttaja Leaderboard — Most Punished"
            suffix = "punishments"
        else:
            ranked = await self.auttaja_db.leaderboard_punishers()
            title = "🏆 Auttaja Leaderboard — Most Active Punishers"
            suffix = "punishments issued"

        if not ranked:
            await interaction.followup.send("No punishment data found.", ephemeral=True)
            return

        total_entries = len(ranked)
        medals = ["🥇", "🥈", "🥉"]
        pages: list[discord.Embed] = []

        for page_index, chunk in enumerate(_chunk(ranked, 10), start=1):
            embed = discord.Embed(
                title=title,
                color=self.embed_color,
                description=(
                    f"**Total entries:** `{total_entries}`\n"
                    f"**Page:** `{page_index}/{(total_entries - 1)//10 + 1}`"
                ),
            )
            lines = []
            for offset, (user_id, count) in enumerate(chunk):
                rank = (page_index - 1) * 10 + offset + 1
                prefix = medals[rank - 1] if rank <= 3 else f"`#{rank}`"
                lines.append(f"{prefix} <@{user_id}> — **{count}** {suffix}")

            embed.add_field(name="Leaderboard", value="\n".join(lines), inline=False)
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.followup.send(embed=pages[0], view=view)

    # ---- /auttaja edit ----

    @auttaja.command(name="edit", description="Edit an Auttaja punishment by its ID")
    @app_commands.describe(id="The punishment ID to edit")
    async def auttaja_edit(self, interaction: discord.Interaction, id: str) -> None:
        await self._staff_check(interaction)

        punishment = await self.auttaja_db.get_punishment(id)
        if punishment is None:
            await interaction.response.send_message(f"No punishment found with ID `{id}`.", ephemeral=True)
            return

        modal = EditAuttajaModal(
            auttaja_db=self.auttaja_db,
            punishment=punishment,
            embed_color=self.embed_color,
            log_channel_id=self.log_channel_id,
        )
        await interaction.response.send_modal(modal)


# ===== SETUP =====


async def setup(bot: commands.Bot) -> None:
    import os

    supabase_url = os.environ.get("SUPABASE_URL") or getattr(bot, "supabase_url", None)
    supabase_key = os.environ.get("SUPABASE_KEY") or getattr(bot, "supabase_key", None)

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the environment "
            "or on the bot instance before loading the Auttaja cog."
        )

    auttaja_db = AuttajaDB(url=supabase_url, key=supabase_key)
    await auttaja_db.connect()

    await bot.add_cog(
        AuttajaCog(
            bot=bot,
            auttaja_db=auttaja_db,
            embed_color=bot.embed_color,  # type: ignore[attr-defined]
            log_channel_id=bot.log_channel_id,  # type: ignore[attr-defined]
            staff_role_id=bot.staff_role_id,  # type: ignore[attr-defined]
        )
    )