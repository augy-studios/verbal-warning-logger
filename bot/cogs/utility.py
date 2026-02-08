from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.db import Database
from bot.ui import PagedEmbedsView
from typing import Literal, List


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db  # type: ignore[attr-defined]

    # ======================
    # BASIC COMMANDS
    # ======================

    @app_commands.command(name="ping", description="Get the bot latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="Pong!",
            description=f"Latency: `{ms} ms`",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="About",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
            description=(
                "Verbal Warnings Logger — Helps you track verbal warnings.\n\n"
                "**Owner:** <@269080651599314944>\n"
                "**Contact:** augy@augystudios.com"
            ),
        )
        await interaction.response.send_message(embed=embed)

    # ======================
    # PAGINATION HELPER
    # ======================

    def _paginate_lines(
        self,
        title: str,
        lines: List[str],
        interaction: discord.Interaction,
    ) -> List[discord.Embed]:
        """Split lines into multiple embeds if >4096 chars (Discord limit)."""

        pages: List[discord.Embed] = []
        chunk: List[str] = []
        current_len = 0

        for line in lines:
            # +1 for newline
            if current_len + len(line) + 1 > 4000:
                embed = discord.Embed(
                    title=title,
                    description="```\n" + "\n".join(chunk) + "\n```",
                    color=self.bot.embed_color,
                )
                pages.append(embed)
                chunk = []
                current_len = 0

            chunk.append(line)
            current_len += len(line) + 1

        if chunk:
            embed = discord.Embed(
                title=title,
                description="```\n" + "\n".join(chunk) + "\n```",
                color=self.bot.embed_color,
            )
            pages.append(embed)

        # Add page footer like verbal.py
        for i, embed in enumerate(pages, start=1):
            embed.set_footer(text=f"Page {i}/{len(pages)}")

        return pages

    # ======================
    # COMMAND GROUP: /retrieveids
    # ======================

    retrieveids = app_commands.Group(
        name="retrieveids",
        description="Retrieve various Discord IDs"
    )

    # ----------------------
    # /retrieveids channels
    # ----------------------

    @retrieveids.command(name="channels", description="Retrieve all channel IDs in a category")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def retrieveids_channels(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:

        await interaction.response.defer(thinking=True)

        if not category.channels:
            await interaction.followup.send("No channels found.", ephemeral=True)
            return

        lines = [f"{c.name} - {c.id}" for c in category.channels]

        pages = self._paginate_lines(
            title=f"Channels in {category.name}",
            lines=lines,
            interaction=interaction,
        )

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0], ephemeral=False)
        else:
            view = PagedEmbedsView(pages, author_id=interaction.user.id)
            await interaction.followup.send(embed=pages[0], view=view, ephemeral=False)

    # ----------------------
    # /retrieveids users
    # ----------------------

    @retrieveids.command(name="users", description="Retrieve all user IDs of members with a role")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def retrieveids_users(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ) -> None:

        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Guild not found.", ephemeral=True)
            return

        members = [m for m in guild.members if role in m.roles]
        if not members:
            await interaction.followup.send("No users found.", ephemeral=True)
            return

        lines = [f"{m.name} - {m.id}" for m in members]

        pages = self._paginate_lines(
            title=f"Users with role {role.name}",
            lines=lines,
            interaction=interaction,
        )

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0], ephemeral=False)
        else:
            view = PagedEmbedsView(pages, author_id=interaction.user.id)
            await interaction.followup.send(embed=pages[0], view=view, ephemeral=False)

    # ----------------------
    # /retrieveids leaderboard
    # ----------------------

    @retrieveids.command(
        name="leaderboard",
        description="Retrieve user IDs from database (mod/offender)"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def retrieveids_leaderboard(
        self,
        interaction: discord.Interaction,
        mode: Literal["offender", "mod"],
    ) -> None:

        await interaction.response.defer(thinking=True)

        warnings = await self.db.list_warnings()
        if not warnings:
            await interaction.followup.send("Database is empty.", ephemeral=True)
            return

        if mode == "offender":
            ids = {w.userId for w in warnings}
            title = "Offenders in Database"
        else:
            ids = {w.modId for w in warnings}
            title = "Moderators in Database"

        lines = []

        for user_id in ids:
            user = interaction.guild.get_member(user_id) if interaction.guild else None
            if user is None:
                try:
                    user = await self.bot.fetch_user(user_id)
                except Exception:
                    lines.append(f"UnknownUser - {user_id}")
                    continue

            lines.append(f"{user.name} - {user_id}")

        if not lines:
            await interaction.followup.send("No users found.", ephemeral=True)
            return

        pages = self._paginate_lines(
            title=title,
            lines=sorted(lines),
            interaction=interaction,
        )

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0], ephemeral=False)
        else:
            view = PagedEmbedsView(pages, author_id=interaction.user.id)
            await interaction.followup.send(embed=pages[0], view=view, ephemeral=False)

    # ----------------------
    # /retrieveids searchusers
    # ----------------------

    @retrieveids.command(
        name="searchusers",
        description="Search the whole server for usernames matching the text"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def retrieveids_searchusers(
        self,
        interaction: discord.Interaction,
        text: str,
    ) -> None:

        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Guild not found.", ephemeral=True)
            return

        search = text.lower()

        matched_members = [
            m for m in guild.members
            if search in m.name.lower() or search in m.display_name.lower()
        ]

        if not matched_members:
            await interaction.followup.send("No users matched your search.", ephemeral=True)
            return

        lines = [f"{m.name} - {m.id}" for m in matched_members]

        pages = self._paginate_lines(
            title=f"Users matching '{text}'",
            lines=sorted(lines),
            interaction=interaction,
        )

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0], ephemeral=False)
        else:
            view = PagedEmbedsView(pages, author_id=interaction.user.id)
            await interaction.followup.send(embed=pages[0], view=view, ephemeral=False)
    
    # ----------------------
    # /retrieveids searchmessages
    # ----------------------

    @retrieveids.command(
        name="searchmessages",
        description="Search server messages from the past 2 weeks matching the text"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def retrieveids_searchmessages(
        self,
        interaction: discord.Interaction,
        text: str,
    ) -> None:

        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Guild not found.", ephemeral=True)
            return

        import datetime

        search = text.lower()
        cutoff = discord.utils.utcnow() - datetime.timedelta(days=14)

        results = []

        for channel in guild.text_channels:
            # Skip channels bot cannot read
            if not channel.permissions_for(guild.me).read_message_history:
                continue

            try:
                async for msg in channel.history(limit=None, after=cutoff):
                    if not msg.content:
                        continue

                    if search in msg.content.lower():
                        # Clean newlines to keep format tidy
                        clean_text = msg.content.replace("\n", " ").strip()

                        results.append(f"{msg.jump_url} - {clean_text}")

            except Exception:
                # Skip inaccessible channels silently
                continue

        if not results:
            await interaction.followup.send(
                "No messages matched your search in the past 2 weeks.",
                ephemeral=True
            )
            return

        pages = self._paginate_lines(
            title=f"Messages matching '{text}' (Last 14 days)",
            lines=results,
            interaction=interaction,
        )

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0], ephemeral=False)
        else:
            view = PagedEmbedsView(pages, author_id=interaction.user.id)
            await interaction.followup.send(embed=pages[0], view=view, ephemeral=False)
    
    # ======================
    # ERROR HANDLER
    # ======================

    @retrieveids_channels.error
    @retrieveids_users.error
    @retrieveids_leaderboard.error
    @retrieveids_searchusers.error
    @retrieveids_searchmessages.error
    async def retrieveids_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ You do not have permission.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCog(bot))
