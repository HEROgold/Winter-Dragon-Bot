"""The /channel-utils command group: delete a whole category, and lock or unlock a channel for a role or member."""

from __future__ import annotations

lazy from typing import TYPE_CHECKING, Annotated

lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_bot.commands import ChannelTypes

# Command resolves option annotations from module globals at runtime, so these must be available here.
lazy from wd_discord import Channel, User, is_network_error
lazy from wd_discord.errors import ApiResponseError, JsonErrorCode
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.permission_solver import PermissionSolver
lazy from wd_discord.permissions import ChannelType, Permissions
lazy from wd_discord.resources.channel import OverwriteParams, OverwriteType
lazy from wd_discord.resources.guild import Role  # noqa: TC002


if TYPE_CHECKING:
    lazy from collections.abc import Iterable

    lazy from wd_bot.commands import Command
    lazy from wd_discord import CommandInteraction, NetworkError
    lazy from wd_discord.entities import PartialGuild
    lazy from wd_discord.resources.channel import PermissionOverwrite


UNLOCKABLE = frozenset(
    {
        ChannelType.DM,
        ChannelType.GROUP_DM,
        ChannelType.PUBLIC_THREAD,
        ChannelType.PRIVATE_THREAD,
        ChannelType.ANNOUNCEMENT_THREAD,
    },
)
"""Channels without their own permission overwrites to lock: DMs and threads."""
DELETE_PERMISSIONS = Permissions.VIEW_CHANNEL | Permissions.MANAGE_CHANNELS
"""What the bot needs on a channel to delete it: Discord answers 50001 Missing Access without VIEW_CHANNEL."""


def locked_overwrite(
    existing: Iterable[PermissionOverwrite],
    target: User | Role,
    *,
    lock: bool,
) -> OverwriteParams:
    """Return ``target``'s overwrite among ``existing`` with SEND_MESSAGES denied (``lock``) or no longer denied.

    Everything else the overwrite allows or denies stays as it was; a target without one starts from nothing.
    """
    overwrite = next((overwrite for overwrite in existing if overwrite.id == target.id), None)
    allow = Permissions(0) if overwrite is None else overwrite.allow
    deny = Permissions(0) if overwrite is None else overwrite.deny
    if lock:
        allow &= ~Permissions.SEND_MESSAGES
        deny |= Permissions.SEND_MESSAGES
    else:
        deny &= ~Permissions.SEND_MESSAGES
    kind = OverwriteType.MEMBER if isinstance(target, User) else OverwriteType.ROLE
    return OverwriteParams(id=target.id, type=kind, allow=allow, deny=deny)


def deleted(result: Channel | NetworkError) -> bool:
    """Whether a channel delete left the channel gone: it succeeded, or the channel was gone already."""
    if not is_network_error(result):
        return True
    return isinstance(result, ApiResponseError) and result.code == JsonErrorCode.UNKNOWN_CHANNEL


def mention(target: User | Role) -> str:
    """Return a clickable mention of the user or role ``target``."""
    return target.mention if isinstance(target, User) else f"<@&{target.id}>"


class ChannelUtils(
    GroupCog,
    name="channel-utils",
    description="Manage channels",
    default_member_permissions=Permissions.MANAGE_CHANNELS,
    contexts=[InteractionContextType.GUILD],
):
    """Moderation helpers for channels: removing a category with its channels, and locking channels."""

    @classmethod
    def _reason(cls, interaction: CommandInteraction, command: Command, action: str) -> str:
        """Return the audit-log reason for ``action``, naming who asked for it and with which command."""
        user = interaction.user
        who = "someone" if user is None else f"{user.username} ({user.id})"
        return f"{action} by {who} using /{cls.path_of(command)}"

    @Cog.command(name="delete-category", description="Delete a category and every channel inside it")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def delete_category(
        self,
        interaction: CommandInteraction,
        category: Annotated[Channel, ChannelTypes(ChannelType.GUILD_CATEGORY)],
    ) -> None:
        """Delete every channel in ``category``, then the category itself.

        Deletes nothing unless the bot may view and manage every one of them.
        """
        guild = interaction.guild
        if guild is None:
            await interaction.respond("This only works in a server.", ephemeral=True)
            return
        app_permissions = interaction.app_permissions
        if app_permissions is not None and DELETE_PERMISSIONS not in app_permissions:
            await interaction.respond("I need the View Channels and Manage Channels permissions to do that.", ephemeral=True)
            return
        await interaction.defer(ephemeral=True)
        doomed = await self._deletable(interaction, guild, category)
        if isinstance(doomed, str):
            await interaction.followup(doomed, ephemeral=True)
            return
        *channels, whole = doomed
        reason = self._reason(interaction, self.delete_category, f"Deleted category {category.name}")
        failed = [channel.name for channel in channels if not deleted(await channel.delete(reason=reason))]
        if failed:
            await interaction.followup(f"I couldn't delete: {', '.join(map(str, failed))}. The category stays.", ephemeral=True)
            return
        if not deleted(await whole.delete(reason=reason)):
            await interaction.followup("I deleted the channels, but couldn't delete the category.", ephemeral=True)
            return
        await interaction.followup(f"Deleted the category {category.name} and its channels.", ephemeral=True)

    @staticmethod
    async def _deletable(interaction: CommandInteraction, guild: PartialGuild, category: Channel) -> list[Channel] | str:
        """Return ``category``'s channels then the category itself, or why the bot may not delete them all.

        The bot's user shares its application's ID, so its member is ``interaction.application_id``.
        """
        full_guild = await guild.fetch()
        bot = await guild.member(interaction.application_id).fetch()
        channels = await guild.channels()
        if is_network_error(full_guild) or is_network_error(bot) or is_network_error(channels):
            return "I couldn't read this server's channels, roles or my own roles."
        channels = list(channels)
        whole = next((channel for channel in channels if channel.id == category.id), None)
        if whole is None:
            return "That category is gone."
        doomed = [*(channel for channel in channels if channel.parent_id == category.id), whole]
        solver = PermissionSolver(full_guild.model, bot.model)
        blocked = [channel.name for channel in doomed if DELETE_PERMISSIONS not in solver.in_channel(channel.model)]
        if blocked:
            return (
                f"I can't see or manage: {', '.join(map(str, blocked))}. Give me View Channel and Manage Channels there, "
                "then try again. Nothing was deleted."
            )
        return doomed

    @Cog.command(name="lock", description="Stop a role or member from sending messages in this channel")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def lock(self, interaction: CommandInteraction, target: User | Role) -> None:
        """Deny ``target`` SEND_MESSAGES in the channel the command was used in."""
        await self._set_lock(interaction, target, lock=True)

    @Cog.command(name="unlock", description="Let a role or member send messages in this channel again")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def unlock(self, interaction: CommandInteraction, target: User | Role) -> None:
        """Stop denying ``target`` SEND_MESSAGES in the channel the command was used in."""
        await self._set_lock(interaction, target, lock=False)

    async def _set_lock(self, interaction: CommandInteraction, target: User | Role, *, lock: bool) -> None:
        """Lock or unlock the interaction's channel for ``target``; remove the overwrite if nothing is left in it."""
        partial = interaction.channel
        channel = None if partial is None else await partial.fetch()
        if channel is None or is_network_error(channel):
            await interaction.respond("I couldn't read this channel.", ephemeral=True)
            return
        if channel.type in UNLOCKABLE:
            await interaction.respond("You can't lock or unlock this channel.", ephemeral=True)
            return
        existing = channel.model.permission_overwrites or []
        overwrite = locked_overwrite(existing, target, lock=lock)
        action = "Locked" if lock else "Unlocked"
        reason = self._reason(interaction, self.lock if lock else self.unlock, f"{action} for {target.id}")
        if overwrite.allow or overwrite.deny:
            failure = await channel.set_permissions(overwrite, reason=reason)
        elif any(old.id == target.id for old in existing):
            failure = await channel.delete_permissions(overwrite.id, reason=reason)
        else:
            failure = None  # nothing was denied, so there's nothing to undo
        if failure is not None:
            await interaction.respond(f"I couldn't change the permissions here: {failure}", ephemeral=True)
            return
        await interaction.respond(f"{action} this channel for {mention(target)}.", ephemeral=True)
