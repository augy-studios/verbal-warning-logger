from __future__ import annotations

import discord
from discord import app_commands


def has_staff_role_or_above(staff_role_id: int) -> app_commands.Check:
    """Allow members who have the staff role OR any role higher than it in the role list."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False

        member = interaction.user
        if not isinstance(member, discord.Member):
            return False

        # Always allow admins.
        if member.guild_permissions.administrator:
            return True

        staff_role = interaction.guild.get_role(staff_role_id)
        if staff_role is None:
            # Misconfigured role id
            raise app_commands.CheckFailure("STAFF_ROLE_ID is invalid (role not found).")

        # Has the role directly
        if staff_role in member.roles:
            return True

        # Or any role with position >= staff role position
        return any(r.position >= staff_role.position for r in member.roles)

    return app_commands.check(predicate)