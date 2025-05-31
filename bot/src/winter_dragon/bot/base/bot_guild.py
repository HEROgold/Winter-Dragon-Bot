"""Cog for managing the bot's guild."""

from discord import Guild, Invite, Member, Permissions, Role
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog
from winter_dragon.bot.settings import Settings


class GuildInitializer(Cog):
    """Cog for managing the bot's guild."""

    invite: Invite
    admin_role: Role
    bot_name = Settings.bot_name

    async def cog_load(self) -> None:
        """Create a guild for this bot if it doesn't exist, and invite the owners."""
        await super().cog_load()
        if Settings.support_guild_id != 0:
            return
        self.logger.warning("Support guild id is not set. Creating new guild.")
        guild = await self._create_guild()
        self.admin_role = await self._create_admin_role(guild)
        self.invite = await self._create_guild_invite(guild)
        Settings.support_guild_id = guild.id
        await self._invite_owners(guild)

    async def _invite_owners(self, guild: Guild) -> None:
        if self.bot.owner_ids is None:
            return
        for owner_id in self.bot.owner_ids:
            owner = await self.bot.fetch_user(owner_id)
            self.logger.info(f"Inviting {owner} to {guild.name}")
            await owner.send(f"Invite to {self.bot_name}'s official discord server: {self.invite}")

    async def _create_guild_invite(self, guild: Guild) -> Invite:
        return await guild.channels[0].create_invite()

    async def _create_guild(self) -> Guild:
        guild = await self.bot.create_guild(name=f"{self.bot_name} Support Guild")
        Settings.support_guild_id = guild.id
        return guild

    async def _create_admin_role(self, guild: Guild) -> Role:
        return await guild.create_role(name="Admin", permissions=Permissions.all())

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        """Send a message to the bot owner when a new member joins."""
        if self.bot.owner_ids is None:
            self.logger.warning("Owner ids are not set. Cannot give admin role.")
            return
        if member.id not in self.bot.owner_ids:
            self.logger.warning(f"{member} is not an owner. Cannot give admin role.")
            return
        if member.guild.id != Settings.support_guild_id:
            self.logger.debug(f"{member.guild} is not the support guild. Cannot give admin role.")
            return
        await member.add_roles(await member.guild.get_role(self.admin_role.id)) # type: ignore[reportUnknownArgumentType]

async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(GuildInitializer(bot=bot))
