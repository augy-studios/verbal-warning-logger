from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.db import Database


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

        if not category.channels:
            await interaction.response.send_message("No channels found.", ephemeral=True)
            return

        lines = [
            f"{channel.name} - {channel.id}"
            for channel in category.channels
        ]

        embed = discord.Embed(
            title=f"Channels in {category.name}",
            description="```\n" + "\n".join(lines) + "\n```",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

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

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Guild not found.", ephemeral=True)
            return

        members = [m for m in guild.members if role in m.roles]

        if not members:
            await interaction.response.send_message("No users found.", ephemeral=True)
            return

        lines = [
            f"{member.name} - {member.id}"
            for member in members
        ]

        embed = discord.Embed(
            title=f"Users with role {role.name}",
            description="```\n" + "\n".join(lines) + "\n```",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

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
        mode: discord.app_commands.Choice[str],
    ) -> None:
        pass  # placeholder for type hinting

    @retrieveids_leaderboard.autocomplete("mode")
    async def leaderboard_mode_autocomplete(self, interaction, current: str):
        return [
            app_commands.Choice(name="mod", value="mod"),
            app_commands.Choice(name="offender", value="offender"),
        ]

    @retrieveids_leaderboard.callback
    async def retrieveids_leaderboard_callback(self, interaction: discord.Interaction, mode: str):

        warnings = await self.db.list_warnings()
        if not warnings:
            await interaction.response.send_message("Database is empty.", ephemeral=True)
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
            await interaction.response.send_message("No users found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description="```\n" + "\n".join(sorted(lines)) + "\n```",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ======================
    # ERROR HANDLER
    # ======================

    @retrieveids_channels.error
    @retrieveids_users.error
    @retrieveids_leaderboard.error
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
