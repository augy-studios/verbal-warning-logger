from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        await interaction.response.send_message(embed=embed, ephemeral=False)

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
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ======================
    # COMMAND GROUP: /retrieveids
    # ======================

    retrieveids = app_commands.Group(
        name="retrieveids",
        description="Retrieve various Discord IDs"
    )

    # /retrieveids channels <category>
    @retrieveids.command(name="channels", description="Retrieve all channel IDs in a category")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def retrieveids_channels(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
    ) -> None:
        channel_ids = [str(channel.id) for channel in category.channels]

        if not channel_ids:
            await interaction.response.send_message(
                "No channels found in this category.",
                ephemeral=True,
            )
            return

        ids_text = "\n".join(channel_ids)

        embed = discord.Embed(
            title=f"Channel IDs in {category.name}",
            description=f"```\n{ids_text}\n```",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    # /retrieveids users <role>
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

        # Reliable method: scan guild members instead of role.members
        member_ids = [str(member.id) for member in guild.members if role in member.roles]

        if not member_ids:
            await interaction.response.send_message(
                "No users found with this role.",
                ephemeral=True,
            )
            return

        ids_text = "\n".join(member_ids)

        embed = discord.Embed(
            title=f"User IDs with role {role.name}",
            description=f"```\n{ids_text}\n```",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ======================
    # ERROR HANDLER
    # ======================

    @retrieveids_channels.error
    @retrieveids_users.error
    async def retrieveids_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot: commands.Bot) -> None:
    cog = UtilityCog(bot)
    await bot.add_cog(cog)
