from __future__ import annotations

from collections import Counter
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from checks import has_staff_role_or_above
from db import Database, VerbalWarning
from ui import PagedEmbedsView


def _is_discord_message_link(link: str) -> bool:
    # Accepts both discord.com and canary/ptb variants.
    link = link.strip()
    return (
        link.startswith("https://discord.com/channels/")
        or link.startswith("https://ptb.discord.com/channels/")
        or link.startswith("https://canary.discord.com/channels/")
    )


def _mention(user_id: int) -> str:
    return f"<@{user_id}>"


def _chunk(seq: list[VerbalWarning], size: int) -> list[list[VerbalWarning]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


class EditVerbalModal(discord.ui.Modal, title="Edit verbal warning"):
    def __init__(
        self,
        db: Database,
        warning: VerbalWarning,
        embed_color: int,
        log_channel_id: int,
    ) -> None:
        super().__init__(timeout=300)
        self.db = db
        self.warning = warning
        self.embed_color = embed_color
        self.log_channel_id = log_channel_id

        self.user_id = discord.ui.TextInput(
            label="User ID",
            placeholder="e.g. 123456789012345678",
            default=str(warning.userId),
            max_length=25,
        )
        self.mod_id = discord.ui.TextInput(
            label="Mod ID",
            placeholder="e.g. 123456789012345678",
            default=str(warning.modId),
            max_length=25,
        )
        self.evidence = discord.ui.TextInput(
            label="Evidence message link",
            placeholder="https://discord.com/channels/...",
            default=warning.evidenceLink,
            max_length=300,
        )
        self.reason = discord.ui.TextInput(
            label="Reason",
            style=discord.TextStyle.paragraph,
            default=warning.reason,
            max_length=1000,
        )

        self.add_item(self.user_id)
        self.add_item(self.mod_id)
        self.add_item(self.evidence)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            user_id = int(self.user_id.value.strip())
            mod_id = int(self.mod_id.value.strip())
        except ValueError:
            await interaction.response.send_message("User ID and Mod ID must be numbers.", ephemeral=True)
            return

        evidence_link = self.evidence.value.strip()
        if not _is_discord_message_link(evidence_link):
            await interaction.response.send_message(
                "Evidence must be a Discord message link (https://discord.com/channels/...).",
                ephemeral=True,
            )
            return

        reason = self.reason.value.strip()
        if not reason:
            await interaction.response.send_message("Reason cannot be empty.", ephemeral=True)
            return

        changed = await self.db.update_warning(
            warning_id=self.warning.id,
            user_id=user_id,
            reason=reason,
            evidence_link=evidence_link,
            mod_id=mod_id,
        )

        if changed <= 0:
            await interaction.response.send_message("Nothing was updated (ID not found).", ephemeral=True)
            return

        embed = discord.Embed(
            title="Verbal warning updated",
            color=self.embed_color,
            description=(
                f"**ID:** `{self.warning.id}`\n"
                f"**User:** {_mention(user_id)} (`{user_id}`)\n"
                f"**Mod:** {_mention(mod_id)} (`{mod_id}`)\n"
                f"**Evidence:** {evidence_link}\n"
                f"**Reason:** {reason}"
            ),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log
        if interaction.client and isinstance(interaction.client, commands.Bot):
            channel = interaction.client.get_channel(self.log_channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)


class VerbalCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database, embed_color: int, log_channel_id: int, staff_role_id: int):
        self.bot = bot
        self.db = db
        self.embed_color = embed_color
        self.log_channel_id = log_channel_id
        self.staff_role_id = staff_role_id

    verbal = app_commands.Group(name="verbal", description="Track verbal warnings")

    @verbal.command(name="add", description="Add a verbal warning")
    @has_staff_role_or_above(staff_role_id=lambda self: self.staff_role_id)  # type: ignore
    async def add(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str,
        evidence_link: str,
        mod: Optional[discord.User] = None,
    ) -> None:
        # The decorator trick above can't accept lambda directly in discord.py,
        # so we do a runtime check (kept below) and keep the decorator-less check style.
        # NOTE: This function body won't run if we raise early.
        await interaction.response.defer(ephemeral=True)

    # --- runtime-check wrappers (discord.py can't bind self into app_commands.check nicely) ---

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

    # ---------------- actual commands ----------------

    @verbal.command(name="add", description="Add a verbal warning")
    async def verbal_add(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str,
        evidence_link: str,
        mod: Optional[discord.User] = None,
    ) -> None:
        await self._staff_check(interaction)

        evidence_link = evidence_link.strip()
        if not _is_discord_message_link(evidence_link):
            await interaction.response.send_message(
                "Evidence must be a Discord message link (https://discord.com/channels/...).",
                ephemeral=True,
            )
            return

        reason = reason.strip()
        if not reason:
            await interaction.response.send_message("Reason cannot be empty.", ephemeral=True)
            return

        mod_id = mod.id if mod else interaction.user.id
        warning_id = await self.db.add_warning(user.id, reason, evidence_link, mod_id)

        embed = discord.Embed(title="Verbal warning added", color=self.embed_color)
        embed.add_field(name="ID", value=f"`{warning_id}`", inline=True)
        embed.add_field(name="User", value=f"{_mention(user.id)} (`{user.id}`)", inline=False)
        embed.add_field(name="Mod", value=f"{_mention(mod_id)} (`{mod_id}`)", inline=False)
        embed.add_field(name="Evidence", value=evidence_link, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log
        channel = self.bot.get_channel(self.log_channel_id)
        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)

    @verbal.command(name="list", description="List all verbal warnings")
    async def verbal_list(self, interaction: discord.Interaction) -> None:
        await self._staff_check(interaction)

        warnings = await self.db.list_warnings()
        if not warnings:
            await interaction.response.send_message("No verbal warnings found.", ephemeral=True)
            return

        counts = Counter(w.userId for w in warnings)

        pages: list[discord.Embed] = []
        for page_index, chunk in enumerate(_chunk(warnings, 10), start=1):
            embed = discord.Embed(
                title="Verbal warnings",
                color=self.embed_color,
                description=(
                    f"**Total warnings:** `{len(warnings)}`\n"
                    f"**Unique users:** `{len(counts)}`\n"
                    f"**Page:** `{page_index}/{(len(warnings) - 1)//10 + 1}`"
                ),
            )
            for w in chunk:
                embed.add_field(
                    name=f"ID {w.id} • {w.createdAt}",
                    value=(
                        f"**User:** {_mention(w.userId)} (count: `{counts[w.userId]}`)\n"
                        f"**Mod:** {_mention(w.modId)}\n"
                        f"**Evidence:** {w.evidenceLink}\n"
                        f"**Reason:** {w.reason}"
                    ),
                    inline=False,
                )
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

    @verbal.command(name="search", description="Search a user's verbal warnings")
    async def verbal_search(self, interaction: discord.Interaction, user: discord.User) -> None:
        await self._staff_check(interaction)

        warnings = await self.db.search_by_user(user.id)
        if not warnings:
            await interaction.response.send_message(f"No verbal warnings found for {_mention(user.id)}.", ephemeral=True)
            return

        total = len(warnings)
        pages: list[discord.Embed] = []
        for page_index, chunk in enumerate(_chunk(warnings, 10), start=1):
            embed = discord.Embed(
                title="Verbal warnings (user)",
                color=self.embed_color,
                description=(
                    f"**User:** {_mention(user.id)} (`{user.id}`)\n"
                    f"**Total warnings:** `{total}`\n"
                    f"**Page:** `{page_index}/{(total - 1)//10 + 1}`"
                ),
            )
            for w in chunk:
                embed.add_field(
                    name=f"ID {w.id} • {w.createdAt}",
                    value=(
                        f"**Mod:** {_mention(w.modId)}\n"
                        f"**Evidence:** {w.evidenceLink}\n"
                        f"**Reason:** {w.reason}"
                    ),
                    inline=False,
                )
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

    @verbal.command(name="delete", description="Delete a verbal warning by its ID")
    async def verbal_delete(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        existing = await self.db.get_warning(id)
        if existing is None:
            await interaction.response.send_message(f"No warning found with ID `{id}`.", ephemeral=True)
            return

        deleted = await self.db.delete_warning(id)
        if deleted <= 0:
            await interaction.response.send_message("Delete failed (ID not found).", ephemeral=True)
            return

        embed = discord.Embed(title="Verbal warning deleted", color=self.embed_color)
        embed.add_field(name="ID", value=f"`{existing.id}`", inline=True)
        embed.add_field(name="User", value=f"{_mention(existing.userId)} (`{existing.userId}`)", inline=False)
        embed.add_field(name="Mod", value=f"{_mention(existing.modId)} (`{existing.modId}`)", inline=False)
        embed.add_field(name="Evidence", value=existing.evidenceLink, inline=False)
        embed.add_field(name="Reason", value=existing.reason, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        channel = self.bot.get_channel(self.log_channel_id)
        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)

    @verbal.command(name="edit", description="Edit a verbal warning by its ID")
    async def verbal_edit(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        warning = await self.db.get_warning(id)
        if warning is None:
            await interaction.response.send_message(f"No warning found with ID `{id}`.", ephemeral=True)
            return

        modal = EditVerbalModal(
            db=self.db,
            warning=warning,
            embed_color=self.embed_color,
            log_channel_id=self.log_channel_id,
        )
        await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot) -> None:
    # This is loaded in main.py with parameters via bot instance attributes.
    db: Database = bot.db  # type: ignore[attr-defined]
    await bot.add_cog(
        VerbalCog(
            bot=bot,
            db=db,
            embed_color=bot.embed_color,  # type: ignore[attr-defined]
            log_channel_id=bot.log_channel_id,  # type: ignore[attr-defined]
            staff_role_id=bot.staff_role_id,  # type: ignore[attr-defined]
        )
    )