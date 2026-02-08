from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from bot.config import Settings, load_settings
from bot.db import Database


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("verbal-bot")


class VerbalWarningsBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        # Slash commands don't need message content.

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
        )

        # Shared config
        self.settings = settings
        self.embed_color = settings.embed_color
        self.log_channel_id = settings.log_channel_id
        self.staff_role_id = settings.staff_role_id

        # Shared DB
        self.db = Database(path="warnings.db")

    async def setup_hook(self) -> None:
        # DB
        await self.db.connect()
        await self.db.init_schema()

        # Load cogs
        await self.load_extension("bot.cogs.verbal")
        await self.load_extension("bot.cogs.utility")

        # Sync commands globally (can take time) — you can switch to guild sync during dev.
        await self.tree.sync()
        log.info("App commands synced")

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id if self.user else "?")


def main() -> None:
    settings = load_settings()
    bot = VerbalWarningsBot(settings)

    try:
        bot.run(settings.token)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()