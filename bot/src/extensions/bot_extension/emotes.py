# TODO @HEROgold: Allow the bot to create a discord Guild, to add up to 50 custom emojis to the guild
# and to use those emojis in messages etc.
# 000
# TODO @HEROgold: Read and add emoji's to a specific directory to read from.
# 000


from constants import EMOJI_DIR, GUILD_OWNERSHIP_LIMIT
from core.bot import WinterDragon
from core.cogs import Cog
from discord import Attachment, Guild, Interaction, Member, Permissions, User


GUILD_NAME = "Emotes"
EMOTE_MANAGER = "Emote Manager"

class EmoteManager(Cog):
    async def show_emotes(self, interaction: Interaction) -> None:
        """Show all emoji's in one message."""
        msg = ""
        for guild in self.bot.guilds:
            if guild.owner.id == self.bot.user.id:
                for emoji in guild.emojis:
                    msg += str(emoji)
        await interaction.response.send_message(msg)

    async def add_emote(self, interaction: Interaction, emoji: Attachment) -> None:
        guild_counter = 0
        EMOJI_DIR.mkdir(parents=True, exist_ok=True)
        for guild in self.bot.guilds:
            if guild.owner.id == self.bot.user.id and guild.name.startswith(GUILD_NAME):
                guild_counter += 1
                if guild.emoji_limit - len(guild.emojis) > 0:
                    await guild.create_custom_emoji(name=emoji.filename, image=await emoji.read())
                    await interaction.response.send_message(f"Added {emoji.filename}.")
                    self.logger.info(f"Added {emoji.filename} to {guild=}.")
                    return
        if guild_counter < GUILD_OWNERSHIP_LIMIT:
            guild = await self.create_guild(guild_counter)
            guild_counter += 1
            await guild.create_custom_emoji(name=emoji.filename, image=await emoji.read())
        await interaction.response.send_message("All available guilds and emoji's are filled.")

    async def create_guild(self, guild_counter: int) -> Guild:
        guild = await self.bot.create_guild(name=f"{GUILD_NAME} {guild_counter}")
        await guild.create_role(name=EMOTE_MANAGER, permissions=Permissions(administrator=True))
        await self.invite_owners(guild)
        return guild

    async def invite_owners(self, guild: Guild) -> None:
        invite = await guild.channels[0].create_invite()
        owners = self.bot.owner_ids or [self.bot.owner_id] if self.bot.owner_id else []
        for i in owners:
            owner: User = await self.bot.get_user(i)
            owner.send(f"Created guild {guild.name} with invite {invite.url}.")

    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        role = next(role for role in member.guild.roles if role.name == EMOTE_MANAGER)
        await member.add_roles(role)

async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(EmoteManager(bot))
