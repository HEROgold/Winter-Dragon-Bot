"""The /channel-utils command group: delete a whole category, and lock or unlock a channel for a role or member."""

lazy from typing import TYPE_CHECKING, Annotated

from wd_bot.commands import Describe
lazy from wd_bot.cogs import Cog, GroupCog
lazy from wd_bot.commands import ChannelTypes

# Command resolves option annotations from module globals at runtime, so these must be available here.
lazy from wd_discord import Channel, Role, User, is_gone
lazy from wd_discord.interactions import InteractionContextType
lazy from wd_discord.permission_solver import PermissionSolver
lazy from wd_discord.permissions import ChannelType, Permissions
lazy from wd_errors import Refused, unwrap


if TYPE_CHECKING:
    lazy from collections.abc import Iterable

    lazy from wd_discord import GuildCommandInteraction
    lazy from wd_discord.entities import PermissionOverwrite


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


def locked_permissions(
    existing: Iterable[PermissionOverwrite],
    target: User | Role,
    *,
    lock: bool,
) -> tuple[Permissions, Permissions]:
    """Return what ``target``'s overwrite among ``existing`` allows and denies, with SEND_MESSAGES denied or not.

    ``lock`` denies SEND_MESSAGES, otherwise it's no longer denied. Everything else the overwrite allows or denies
    stays as it was; a target without one starts from nothing.
    """
    overwrite = next((overwrite for overwrite in existing if overwrite.id == target.id), None)
    allow = Permissions(0) if overwrite is None else overwrite.allow
    deny = Permissions(0) if overwrite is None else overwrite.deny
    if lock:
        allow &= ~Permissions.SEND_MESSAGES
        deny |= Permissions.SEND_MESSAGES
    else:
        deny &= ~Permissions.SEND_MESSAGES
    return allow, deny


class ChannelUtils(
    GroupCog,
    name="channel-utils",
    description="Manage channels",
    default_member_permissions=Permissions.MANAGE_CHANNELS,
    contexts=[InteractionContextType.GUILD],
):
    """Moderation helpers for channels: removing a category with its channels, and locking channels."""

    @Cog.command(name="delete-category", description="Delete a category and every channel inside it")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def delete_category(
        self,
        interaction: GuildCommandInteraction,
        category: Annotated[Channel, ChannelTypes(ChannelType.GUILD_CATEGORY)],
    ) -> None:
        """Delete every channel in ``category``, then the category itself.

        Deletes nothing unless the bot may view and manage every one of them.
        """
        app_permissions = interaction.app_permissions
        if app_permissions is not None and DELETE_PERMISSIONS not in app_permissions:
            msg = "I need the View Channels and Manage Channels permissions to do that."
            raise Refused(msg)
        await interaction.defer(ephemeral=True)
        *channels, whole = await self._deletable(interaction, category)
        reason = self.audit_reason(interaction, self.delete_category, f"Deleted category {category.name}")
        failed = [channel.name for channel in channels if not is_gone(await channel.delete(reason=reason))]
        if failed:
            msg = f"I couldn't delete: {', '.join(map(str, failed))}. The category stays."
            raise Refused(msg)
        if not is_gone(await whole.delete(reason=reason)):
            msg = "I deleted the channels, but couldn't delete the category."
            raise Refused(msg)
        await interaction.followup(f"Deleted the category {category.name} and its channels.", ephemeral=True)

    @staticmethod
    async def _deletable(interaction: GuildCommandInteraction, category: Channel) -> list[Channel]:
        """Return ``category``'s channels then the category itself; refuse unless the bot may delete them all.

        The bot's user shares its application's ID, so its member is ``interaction.application_id``.
        """
        guild = interaction.guild
        unreadable = "I couldn't read this server's channels, roles or my own roles."
        full_guild = unwrap(await guild.fetch(), unreadable)
        bot = unwrap(await guild.member(interaction.application_id).fetch(), unreadable)
        channels = list(unwrap(await guild.fetch_channels(), unreadable))
        whole = next((channel for channel in channels if channel.id == category.id), None)
        if whole is None:
            msg = "That category is gone."
            raise Refused(msg)
        doomed = [*(channel for channel in channels if channel.parent is not None and channel.parent.id == category.id), whole]
        solver = PermissionSolver(full_guild.model, bot.model)
        blocked = [channel.name for channel in doomed if DELETE_PERMISSIONS not in solver.in_channel(channel.model)]
        if blocked:
            msg = (
                f"I can't see or manage: {', '.join(map(str, blocked))}. Give me View Channel and Manage Channels there, "
                "then try again. Nothing was deleted."
            )
            raise Refused(msg)
        return doomed

    @Cog.command(name="lock", description="Stop a role or member from sending messages in this channel")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def lock(
        self,
        interaction: GuildCommandInteraction,
        target: Annotated[User | Role, Describe("The role or member to lock")],
    ) -> None:
        """Deny ``target`` SEND_MESSAGES in the channel the command was used in."""
        await self._set_lock(interaction, target, lock=True)

    @Cog.command(name="unlock", description="Let a role or member send messages in this channel again")  # pyright: ignore[reportUntypedFunctionDecorator, reportUnknownMemberType, reportAttributeAccessIssue]
    async def unlock(
        self,
        interaction: GuildCommandInteraction,
        target: Annotated[User | Role, Describe("The role or member to unlock")],
    ) -> None:
        """Stop denying ``target`` SEND_MESSAGES in the channel the command was used in."""
        await self._set_lock(interaction, target, lock=False)

    async def _set_lock(self, interaction: GuildCommandInteraction, target: User | Role, *, lock: bool) -> None:
        """Lock or unlock the interaction's channel for ``target``; remove the overwrite if nothing is left in it."""
        channel = unwrap(await interaction.channel.fetch(), "I couldn't read this channel.")
        if channel.type in UNLOCKABLE:
            msg = "You can't lock or unlock this channel."
            raise Refused(msg)
        existing = list(channel.overwrites)
        allow, deny = locked_permissions(existing, target, lock=lock)
        action = "Locked" if lock else "Unlocked"
        reason = self.audit_reason(interaction, self.lock if lock else self.unlock, f"{action} for {target.id}")
        if allow or deny:
            failure = await channel.set_permissions(target, allow=allow, deny=deny, reason=reason)
        elif any(old.id == target.id for old in existing):
            failure = await channel.delete_permissions(target, reason=reason)
        else:
            failure = None  # nothing was denied, so there's nothing to undo
        if failure is not None:
            msg = f"I couldn't change the permissions here: {failure}"
            raise Refused(msg, cause=failure)
        await interaction.respond(f"{action} this channel for {target.mention}.", ephemeral=True)
