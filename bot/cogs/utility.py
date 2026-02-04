from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Get the bot latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        # latency is websocket latency; it's the closest simple proxy for responsiveness.
        ms = round(self.bot.latency * 1000)
        embed = discord.Embed(title="Pong!", description=f"Latency: `{ms} ms`", color=self.bot.embed_color)  # type: ignore[attr-defined]
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="about", description="About this bot")
    async def about(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="About",
            color=self.bot.embed_color,  # type: ignore[attr-defined]
            description=(
                "Verbal Warnings Bot — tracks verbal warnings only.\n\n"
                "**Owner:** Augustine\n"
                "**Contact:** augy@augystudios.com"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCog(bot))