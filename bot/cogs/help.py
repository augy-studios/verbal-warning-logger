from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


# ===== HELP DATA =====
#
# Each entry: cog_name -> (short description, [(syntax, description, example), ...])

_COG_DATA: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "Verbal Warnings": (
        "Track and manage verbal warnings issued to users.",
        [
            (
                "/verbal add <user> <reason> <evidence_link> [mod]",
                "Add a verbal warning. Defaults to you as the issuing mod if `mod` is not provided.",
                "/verbal add @JohnDoe Spamming https://discord.com/channels/... @Moderator",
            ),
            (
                "/verbal list",
                "List all verbal warnings in the database, paginated 10 per page.",
                "/verbal list",
            ),
            (
                "/verbal search <user>",
                "List all verbal warnings for a specific user.",
                "/verbal search @JohnDoe",
            ),
            (
                "/verbal delete <id>",
                "Permanently delete a verbal warning by its ID.",
                "/verbal delete 42",
            ),
            (
                "/verbal edit <id>",
                "Edit a warning's user, mod, evidence link, or reason via a pre-filled modal.",
                "/verbal edit 42",
            ),
            (
                "/verbal lb <mode>",
                "Show a leaderboard. `offender` = most warned users, `mod` = most warnings issued.",
                "/verbal lb offender",
            ),
        ],
    ),
    "Utility": (
        "General utility commands for server management.",
        [
            (
                "/ping",
                "Check the bot's current response latency.",
                "/ping",
            ),
            (
                "/about",
                "Show information about the bot.",
                "/about",
            ),
            (
                "/retrieveids channels <category>",
                "List all channel names and IDs within a category. Requires Manage Channels.",
                "/retrieveids channels Staff Channels",
            ),
            (
                "/retrieveids users <role>",
                "List all usernames and IDs of members with a given role. Requires Manage Roles.",
                "/retrieveids users @Staff",
            ),
            (
                "/retrieveids leaderboard <mode>",
                "List unique user IDs recorded in the warnings database. `offender` or `mod`.",
                "/retrieveids leaderboard mod",
            ),
            (
                "/retrieveids searchusers <text>",
                "Search all server members whose username or display name contains the given text.",
                "/retrieveids searchusers john",
            ),
        ],
    ),
    "Polls": (
        "Create and manage interactive staff evaluation polls with button voting.",
        [
            (
                "/poll create [channel] [anonymous] [max_votes]",
                "Open a modal to create a new poll. `anonymous` hides voter identities (removes Participants button). `max_votes` auto-ends the poll once that many unique votes are cast (0 = unlimited).",
                "/poll create #staff-polls anonymous:True max_votes:10",
            ),
            (
                "/poll edit <id>",
                "Edit a poll's title, description, or option labels via a pre-filled modal. Option count cannot change.",
                "/poll edit 3",
            ),
            (
                "/poll delete <id>",
                "Close and disable a poll. Disables all voting buttons on the original message.",
                "/poll delete 3",
            ),
            (
                "/poll list [filter] [channel] [user]",
                "List polls paginated. Filter: `active` (default) or `all`. Optionally narrow by channel or creator.",
                "/poll list all #staff-polls @Moderator",
            ),
            (
                "/poll view <id>",
                "View a poll's live results and a jump link to the message, shown only to you.",
                "/poll view 3",
            ),
        ],
    ),
    "Poll Templates": (
        "Save poll structures as reusable templates to quickly spin up new polls.",
        [
            (
                "/poll_template create",
                "Create a new template from scratch via a modal (name, description, options).",
                "/poll_template create",
            ),
            (
                "/poll_template from_poll <poll_id>",
                "Convert an existing poll into a template, pre-filling the modal with its data.",
                "/poll_template from_poll 5",
            ),
            (
                "/poll_template edit <id>",
                "Edit a template's name, description, or option labels. Option count cannot change.",
                "/poll_template edit 2",
            ),
            (
                "/poll_template delete <id>",
                "Soft-delete a template so it no longer appears in listings.",
                "/poll_template delete 2",
            ),
            (
                "/poll_template list [filter]",
                "List templates. Filter: `active` (default) or `all` including deleted.",
                "/poll_template list all",
            ),
            (
                "/poll_template view <id>",
                "View a template's full details — name, description, all options, and status.",
                "/poll_template view 2",
            ),
            (
                "/poll_template preview <id>",
                "See an ephemeral preview of what a poll from this template would look like.",
                "/poll_template preview 2",
            ),
            (
                "/poll_template use <id> [channel] [anonymous] [max_votes]",
                "Open a pre-filled modal to review and edit the template before posting it as a live poll. `anonymous` and `max_votes` override the template's stored settings.",
                "/poll_template use 2 #staff-polls anonymous:True max_votes:10",
            ),
        ],
    ),
}

_COG_EMOJIS: dict[str, str] = {
    "Verbal Warnings": "⚠️",
    "Utility": "🔧",
    "Polls": "📊",
    "Poll Templates": "📋",
}


# ===== EMBED BUILDERS =====


def _build_home_embed(embed_color: int) -> discord.Embed:
    lines = [
        f"{_COG_EMOJIS.get(name, '•')} **{name}** — {desc}"
        for name, (desc, _) in _COG_DATA.items()
    ]
    embed = discord.Embed(
        title="Help",
        color=embed_color,
        description="Select a category below to view its commands.\n\n" + "\n".join(lines),
    )
    embed.set_footer(text="<required>  [optional]")
    return embed


def _build_cog_embed(cog_name: str, embed_color: int) -> discord.Embed:
    desc, command_entries = _COG_DATA[cog_name]
    emoji = _COG_EMOJIS.get(cog_name, "")
    embed = discord.Embed(
        title=f"{emoji} {cog_name}",
        color=embed_color,
        description=desc,
    )
    for syntax, description, example in command_entries:
        embed.add_field(
            name=f"`{syntax}`",
            value=f"{description}\n**Example:** `{example}`",
            inline=False,
        )
    embed.set_footer(text="<required>  [optional]  •  Use the buttons to navigate categories")
    return embed


# ===== UI =====


class HomeButton(discord.ui.Button["HelpView"]):
    def __init__(self, embed_color: int) -> None:
        super().__init__(label="Home", emoji="🏠", style=discord.ButtonStyle.secondary)
        self._embed_color = embed_color

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        self.view._set_active(None)
        await interaction.response.edit_message(
            embed=_build_home_embed(self._embed_color), view=self.view
        )


class CogButton(discord.ui.Button["HelpView"]):
    def __init__(self, cog_name: str, embed_color: int) -> None:
        super().__init__(
            label=cog_name,
            emoji=_COG_EMOJIS.get(cog_name),
            style=discord.ButtonStyle.primary,
        )
        self._cog_name = cog_name
        self._embed_color = embed_color

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        self.view._set_active(self._cog_name)
        await interaction.response.edit_message(
            embed=_build_cog_embed(self._cog_name, self._embed_color), view=self.view
        )


class HelpView(discord.ui.View):
    def __init__(self, embed_color: int, author_id: int) -> None:
        super().__init__(timeout=180)
        self._embed_color = embed_color
        self._author_id = author_id

        self._home_btn = HomeButton(embed_color=embed_color)
        self._home_btn.disabled = True  # already on home
        self.add_item(self._home_btn)

        self._cog_buttons: dict[str, CogButton] = {}
        for cog_name in _COG_DATA:
            btn = CogButton(cog_name=cog_name, embed_color=embed_color)
            self._cog_buttons[cog_name] = btn
            self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self._author_id

    def _set_active(self, cog_name: str | None) -> None:
        """Highlight the active category button and re-enable all others."""
        self._home_btn.disabled = cog_name is None
        for name, btn in self._cog_buttons.items():
            btn.disabled = name == cog_name
            btn.style = (
                discord.ButtonStyle.secondary
                if name == cog_name
                else discord.ButtonStyle.primary
            )


# ===== COG =====


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot, embed_color: int) -> None:
        self.bot = bot
        self.embed_color = embed_color

    @app_commands.command(name="help", description="Show all bot commands organised by category")
    async def help_command(self, interaction: discord.Interaction) -> None:
        embed = _build_home_embed(self.embed_color)
        view = HelpView(embed_color=self.embed_color, author_id=interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)


# ===== SETUP =====


async def setup(bot: commands.Bot) -> None:
    embed_color: int = getattr(bot, "embed_color", 0x007FFF)
    await bot.add_cog(HelpCog(bot=bot, embed_color=embed_color))
