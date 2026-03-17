from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from bot.ui import PagedEmbedsView
from bot.cogs.polls import (
    StaffPollDatabase,
    StaffPollVoteView,
    _build_poll_embed,
    _parse_options,
    _resolve_username,
)


# ===== DATABASE =====


@dataclass(slots=True)
class PollTemplate:
    id: int
    name: str
    description: str
    created_at: str
    created_by: int
    is_deleted: bool


@dataclass(slots=True)
class PollTemplateOption:
    id: int
    template_id: int
    label: str
    display_order: int


class PollTemplateDatabase:
    def __init__(self, path: str = "polltemplates.db") -> None:
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
            raise RuntimeError("PollTemplateDatabase is not connected")
        return self._conn

    async def init_schema(self) -> None:
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS poll_templates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                description TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                created_by  INTEGER NOT NULL,
                is_deleted  INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS poll_template_options (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id   INTEGER NOT NULL REFERENCES poll_templates(id) ON DELETE CASCADE,
                label         TEXT    NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pt_deleted ON poll_templates(is_deleted)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pto_template ON poll_template_options(template_id)"
        )
        await self.conn.commit()

    async def create_template(self, name: str, description: str, created_by: int) -> int:
        cur = await self.conn.execute(
            "INSERT INTO poll_templates (name, description, created_by) VALUES (?, ?, ?)",
            (name, description, created_by),
        )
        await self.conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    async def get_template(self, template_id: int) -> Optional[PollTemplate]:
        cur = await self.conn.execute(
            "SELECT id, name, description, created_at, created_by, is_deleted "
            "FROM poll_templates WHERE id = ?",
            (template_id,),
        )
        return _row_to_template(await cur.fetchone())

    async def list_templates(self, include_deleted: bool = False) -> list[PollTemplate]:
        sql = (
            "SELECT id, name, description, created_at, created_by, is_deleted "
            "FROM poll_templates"
        )
        if not include_deleted:
            sql += " WHERE is_deleted = 0"
        sql += " ORDER BY id DESC"
        cur = await self.conn.execute(sql)
        return [t for t in (_row_to_template(r) for r in await cur.fetchall()) if t is not None]

    async def update_template(self, template_id: int, name: str, description: str) -> int:
        cur = await self.conn.execute(
            "UPDATE poll_templates SET name = ?, description = ? WHERE id = ?",
            (name, description, template_id),
        )
        await self.conn.commit()
        return cur.rowcount

    async def delete_template(self, template_id: int) -> int:
        cur = await self.conn.execute(
            "UPDATE poll_templates SET is_deleted = 1 WHERE id = ?", (template_id,)
        )
        await self.conn.commit()
        return cur.rowcount

    async def add_options(self, template_id: int, labels: list[str]) -> None:
        for order, label in enumerate(labels):
            await self.conn.execute(
                "INSERT INTO poll_template_options (template_id, label, display_order) VALUES (?, ?, ?)",
                (template_id, label, order),
            )
        await self.conn.commit()

    async def get_options(self, template_id: int) -> list[PollTemplateOption]:
        cur = await self.conn.execute(
            "SELECT id, template_id, label, display_order FROM poll_template_options "
            "WHERE template_id = ? ORDER BY display_order",
            (template_id,),
        )
        return [
            PollTemplateOption(
                id=int(r["id"]),
                template_id=int(r["template_id"]),
                label=str(r["label"]),
                display_order=int(r["display_order"]),
            )
            for r in await cur.fetchall()
        ]

    async def update_option_labels(
        self, options: list[PollTemplateOption], new_labels: list[str]
    ) -> None:
        for option, label in zip(options, new_labels):
            await self.conn.execute(
                "UPDATE poll_template_options SET label = ? WHERE id = ?", (label, option.id)
            )
        await self.conn.commit()


# ===== HELPERS =====


def _row_to_template(row: aiosqlite.Row | None) -> Optional[PollTemplate]:
    if row is None:
        return None
    return PollTemplate(
        id=int(row["id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        created_at=str(row["created_at"]),
        created_by=int(row["created_by"]),
        is_deleted=bool(row["is_deleted"]),
    )


def _chunk(seq: list, size: int) -> list[list]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def _build_template_detail_embed(
    template: PollTemplate,
    options: list[PollTemplateOption],
    embed_color: int,
    created_by_name: str = "",
) -> discord.Embed:
    status = "Deleted" if template.is_deleted else "Active"
    embed = discord.Embed(
        title=f"Template #{template.id} — {template.name}",
        color=0x808080 if template.is_deleted else embed_color,
        description=template.description if template.description else "*No description*",
    )
    embed.add_field(
        name="Options",
        value="\n".join(f"`{i + 1}.` {o.label}" for i, o in enumerate(options)) or "*None*",
        inline=False,
    )
    embed.set_footer(
        text=(
            f"Status: {status} • Created: {template.created_at} • "
            f"Created by {created_by_name or str(template.created_by)}"
        )
    )
    return embed


def _build_template_preview_embed(
    template: PollTemplate,
    options: list[PollTemplateOption],
    embed_color: int,
    created_by_name: str = "",
) -> discord.Embed:
    embed = discord.Embed(
        title=template.name,
        color=embed_color,
        description=template.description if template.description else None,
    )
    for option in options:
        embed.add_field(
            name=option.label,
            value="░░░░░░░░░░ **0** votes (0.0%)",
            inline=False,
        )
    embed.set_author(name="Preview — this is not a live poll")
    embed.set_footer(
        text=(
            f"Template #{template.id} • "
            f"Created by {created_by_name or str(template.created_by)}"
        )
    )
    return embed


# ===== MODALS =====


def _validate_options(
    options: list[str], interaction_response: discord.InteractionResponse
) -> str | None:
    """Returns an error message string if invalid, else None."""
    if len(options) < 2:
        return "You must provide at least 2 options, one per line."
    if len(options) > 24:
        return "You can have at most 24 options."
    if any(len(o) > 80 for o in options):
        return "Each option label must be 80 characters or fewer."
    return None


class CreateTemplateModal(discord.ui.Modal, title="Create poll template"):
    template_name = discord.ui.TextInput(
        label="Template name",
        placeholder="e.g. Standard Staff Evaluation",
        max_length=200,
    )
    template_description = discord.ui.TextInput(
        label="Description (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="Additional context shown on polls created from this template.",
        required=False,
        max_length=500,
    )
    template_options = discord.ui.TextInput(
        label="Options (one per line, minimum 2)",
        style=discord.TextStyle.paragraph,
        placeholder="Promote\nRetain\nDemote",
        max_length=1000,
    )

    def __init__(self, template_db: PollTemplateDatabase, embed_color: int) -> None:
        super().__init__(timeout=300)
        self._template_db = template_db
        self._embed_color = embed_color

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = self.template_name.value.strip()
        description = self.template_description.value.strip() if self.template_description.value else ""
        options = _parse_options(self.template_options.value)

        error = _validate_options(options, interaction.response)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        template_id = await self._template_db.create_template(name, description, interaction.user.id)
        await self._template_db.add_options(template_id, options)

        embed = discord.Embed(
            title="Template created",
            color=self._embed_color,
            description=(
                f"**ID:** `{template_id}`\n"
                f"**Name:** {name}\n"
                f"**Options:** {len(options)}\n\n"
                f"Use `/poll_template use {template_id}` to post a poll from this template."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConvertPollToTemplateModal(discord.ui.Modal, title="Convert poll to template"):
    template_name = discord.ui.TextInput(label="Template name", max_length=200)
    template_description = discord.ui.TextInput(
        label="Description (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    template_options = discord.ui.TextInput(
        label="Options (one per line, minimum 2)",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(
        self,
        template_db: PollTemplateDatabase,
        embed_color: int,
        prefill_name: str,
        prefill_description: str,
        prefill_options: list[str],
    ) -> None:
        super().__init__(timeout=300)
        self._template_db = template_db
        self._embed_color = embed_color
        self.template_name.default = prefill_name[:200]
        self.template_description.default = prefill_description[:500]
        self.template_options.default = "\n".join(prefill_options)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = self.template_name.value.strip()
        description = self.template_description.value.strip() if self.template_description.value else ""
        options = _parse_options(self.template_options.value)

        error = _validate_options(options, interaction.response)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        template_id = await self._template_db.create_template(name, description, interaction.user.id)
        await self._template_db.add_options(template_id, options)

        embed = discord.Embed(
            title="Poll converted to template",
            color=self._embed_color,
            description=(
                f"**Template ID:** `{template_id}`\n"
                f"**Name:** {name}\n"
                f"**Options:** {len(options)}\n\n"
                f"Use `/poll_template use {template_id}` to post a poll from this template."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class UseTemplateModal(discord.ui.Modal, title="Create poll from template"):
    poll_title = discord.ui.TextInput(label="Poll title", max_length=200)
    poll_description = discord.ui.TextInput(
        label="Description (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    poll_options = discord.ui.TextInput(
        label="Options (one per line, minimum 2)",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(
        self,
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        target_channel: discord.TextChannel,
        prefill_name: str,
        prefill_description: str,
        prefill_options: list[str],
    ) -> None:
        super().__init__(timeout=300)
        self._staffpoll_db = staffpoll_db
        self._embed_color = embed_color
        self._target_channel = target_channel
        self.poll_title.default = prefill_name[:200]
        self.poll_description.default = prefill_description[:500]
        self.poll_options.default = "\n".join(prefill_options)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        title = self.poll_title.value.strip()
        description = self.poll_description.value.strip() if self.poll_description.value else ""
        options = _parse_options(self.poll_options.value)

        error = _validate_options(options, interaction.response)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        poll_id = await self._staffpoll_db.create_poll(title, description, interaction.user.id)
        await self._staffpoll_db.add_options(poll_id, options)

        poll = await self._staffpoll_db.get_poll(poll_id)
        staffpoll_options = await self._staffpoll_db.get_options(poll_id)
        assert poll is not None

        embed = _build_poll_embed(
            poll, staffpoll_options, {}, self._embed_color, interaction.user.name
        )
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
            f"Poll posted in {self._target_channel.mention}!"
            if self._target_channel.id != interaction.channel_id
            else "Poll posted!"
        )
        await interaction.followup.send(confirm, ephemeral=True)


class EditTemplateModal(discord.ui.Modal, title="Edit poll template"):
    template_name = discord.ui.TextInput(label="Template name", max_length=200)
    template_description = discord.ui.TextInput(
        label="Description (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    template_options = discord.ui.TextInput(
        label="Options (one per line, minimum 2)",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(
        self,
        template_db: PollTemplateDatabase,
        embed_color: int,
        template: PollTemplate,
        options: list[PollTemplateOption],
    ) -> None:
        super().__init__(timeout=300)
        self._template_db = template_db
        self._embed_color = embed_color
        self._template = template
        self._options = options
        self.template_name.default = template.name
        self.template_description.default = template.description
        self.template_options.default = "\n".join(o.label for o in options)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = self.template_name.value.strip()
        description = self.template_description.value.strip() if self.template_description.value else ""
        new_labels = _parse_options(self.template_options.value)

        error = _validate_options(new_labels, interaction.response)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        if len(new_labels) != len(self._options):
            await interaction.response.send_message(
                f"Option count cannot change ({len(self._options)} → {len(new_labels)}). "
                "Delete and recreate the template to change the number of options.",
                ephemeral=True,
            )
            return

        await self._template_db.update_template(self._template.id, name, description)
        await self._template_db.update_option_labels(self._options, new_labels)
        await interaction.response.send_message(
            f"Template `#{self._template.id}` updated.", ephemeral=True
        )


# ===== COG =====


class PollTemplateCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        template_db: PollTemplateDatabase,
        staffpoll_db: StaffPollDatabase,
        embed_color: int,
        staff_role_id: int,
    ) -> None:
        self.bot = bot
        self.template_db = template_db
        self.staffpoll_db = staffpoll_db
        self.embed_color = embed_color
        self.staff_role_id = staff_role_id

    async def cog_unload(self) -> None:
        await self.template_db.close()
        await self.staffpoll_db.close()

    poll_template = app_commands.Group(name="poll_template", description="Manage poll templates")

    async def _staff_check(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            raise app_commands.CheckFailure("This command can only be used in a server.")
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
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

    @poll_template.command(name="create", description="Create a new poll template from scratch")
    async def template_create(self, interaction: discord.Interaction) -> None:
        await self._staff_check(interaction)
        modal = CreateTemplateModal(template_db=self.template_db, embed_color=self.embed_color)
        await interaction.response.send_modal(modal)

    @poll_template.command(name="from_poll", description="Convert an existing poll into a reusable template")
    @app_commands.describe(poll_id="ID of the poll to convert")
    async def template_from_poll(self, interaction: discord.Interaction, poll_id: int) -> None:
        await self._staff_check(interaction)

        poll = await self.staffpoll_db.get_poll(poll_id)
        if poll is None:
            await interaction.response.send_message(
                f"No poll found with ID `{poll_id}`.", ephemeral=True
            )
            return

        options = await self.staffpoll_db.get_options(poll_id)
        modal = ConvertPollToTemplateModal(
            template_db=self.template_db,
            embed_color=self.embed_color,
            prefill_name=poll.title,
            prefill_description=poll.description,
            prefill_options=[o.label for o in options],
        )
        await interaction.response.send_modal(modal)

    @poll_template.command(name="edit", description="Edit a template's name, description, or option labels")
    @app_commands.describe(id="ID of the template to edit")
    async def template_edit(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        template = await self.template_db.get_template(id)
        if template is None or template.is_deleted:
            await interaction.response.send_message(
                f"No active template found with ID `{id}`.", ephemeral=True
            )
            return

        options = await self.template_db.get_options(id)
        modal = EditTemplateModal(
            template_db=self.template_db,
            embed_color=self.embed_color,
            template=template,
            options=options,
        )
        await interaction.response.send_modal(modal)

    @poll_template.command(name="delete", description="Delete a poll template")
    @app_commands.describe(id="ID of the template to delete")
    async def template_delete(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        template = await self.template_db.get_template(id)
        if template is None or template.is_deleted:
            await interaction.response.send_message(
                f"No active template found with ID `{id}`.", ephemeral=True
            )
            return

        await self.template_db.delete_template(id)
        await interaction.response.send_message(
            f"Template `#{id}` — **{template.name}** has been deleted.", ephemeral=True
        )

    @poll_template.command(name="list", description="List poll templates")
    @app_commands.describe(filter="Show active templates only, or all including deleted")
    async def template_list(
        self,
        interaction: discord.Interaction,
        filter: Literal["active", "all"] = "active",
    ) -> None:
        await self._staff_check(interaction)

        templates = await self.template_db.list_templates(include_deleted=(filter == "all"))
        if not templates:
            label = "active " if filter == "active" else ""
            await interaction.response.send_message(
                f"No {label}poll templates found.", ephemeral=True
            )
            return

        pages: list[discord.Embed] = []
        total_pages = (len(templates) - 1) // 10 + 1

        for page_index, chunk in enumerate(_chunk(templates, 10), start=1):
            embed = discord.Embed(
                title="Poll templates",
                color=self.embed_color,
                description=(
                    f"**Total:** `{len(templates)}`\n"
                    f"**Filter:** `{filter}`\n"
                    f"**Page:** `{page_index}/{total_pages}`"
                ),
            )
            for t in chunk:
                status = "Deleted" if t.is_deleted else "Active"
                options = await self.template_db.get_options(t.id)
                embed.add_field(
                    name=f"#{t.id} — {t.name}",
                    value=(
                        f"**Status:** {status}\n"
                        f"**Options:** {len(options)}\n"
                        f"**Created:** {t.created_at}\n"
                        f"**By:** <@{t.created_by}>"
                    ),
                    inline=False,
                )
            pages.append(embed)

        view = PagedEmbedsView(pages, author_id=interaction.user.id)
        await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)

    @poll_template.command(name="view", description="View details and options for a poll template")
    @app_commands.describe(id="ID of the template to view")
    async def template_view(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        template = await self.template_db.get_template(id)
        if template is None:
            await interaction.response.send_message(
                f"No template found with ID `{id}`.", ephemeral=True
            )
            return

        options = await self.template_db.get_options(id)
        created_by_name = await _resolve_username(interaction.client, template.created_by)  # type: ignore[arg-type]
        embed = _build_template_detail_embed(template, options, self.embed_color, created_by_name)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @poll_template.command(name="preview", description="Preview what a poll from this template would look like")
    @app_commands.describe(id="ID of the template to preview")
    async def template_preview(self, interaction: discord.Interaction, id: int) -> None:
        await self._staff_check(interaction)

        template = await self.template_db.get_template(id)
        if template is None or template.is_deleted:
            await interaction.response.send_message(
                f"No active template found with ID `{id}`.", ephemeral=True
            )
            return

        options = await self.template_db.get_options(id)
        created_by_name = await _resolve_username(interaction.client, template.created_by)  # type: ignore[arg-type]
        embed = _build_template_preview_embed(template, options, self.embed_color, created_by_name)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @poll_template.command(name="use", description="Create and post a poll from an existing template")
    @app_commands.describe(
        id="ID of the template to use",
        channel="Channel to post the poll in (defaults to current channel)",
    )
    async def template_use(
        self,
        interaction: discord.Interaction,
        id: int,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        await self._staff_check(interaction)

        template = await self.template_db.get_template(id)
        if template is None or template.is_deleted:
            await interaction.response.send_message(
                f"No active template found with ID `{id}`.", ephemeral=True
            )
            return

        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message(
                "Please specify a text channel or run this in one.", ephemeral=True
            )
            return

        template_options = await self.template_db.get_options(id)
        modal = UseTemplateModal(
            staffpoll_db=self.staffpoll_db,
            embed_color=self.embed_color,
            target_channel=target,
            prefill_name=template.name,
            prefill_description=template.description,
            prefill_options=[o.label for o in template_options],
        )
        await interaction.response.send_modal(modal)


# ===== SETUP =====


async def setup(bot: commands.Bot) -> None:
    template_db = PollTemplateDatabase()
    await template_db.connect()
    await template_db.init_schema()

    # Separate connection to staffpolls.db so the `use` command can create real polls.
    # WAL mode on staffpolls.db allows concurrent readers/writers safely.
    staffpoll_db = StaffPollDatabase()
    await staffpoll_db.connect()
    # Schema already initialised by polls.py; calling init_schema again is a no-op.
    await staffpoll_db.init_schema()

    embed_color: int = getattr(bot, "embed_color", 0x007FFF)
    staff_role_id: int = getattr(bot, "staff_role_id", 0)

    await bot.add_cog(
        PollTemplateCog(
            bot=bot,
            template_db=template_db,
            staffpoll_db=staffpoll_db,
            embed_color=embed_color,
            staff_role_id=staff_role_id,
        )
    )
