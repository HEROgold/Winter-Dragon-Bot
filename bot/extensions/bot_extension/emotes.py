# TODO: Allow the bot to create a discord Guild, to add up to 50 custom emojis to the guild, and to use those emojis in messages etc.
# TODO: Read and add emoji's to a specific directory to read from.


from discord import Attachment, Interaction

from bot import WinterDragon
from bot._types.cogs import Cog
from bot.constants import EMOJI_DIR, GUILD_OWNERSHIP_LIMIT


GUILD_NAME = "Emotes"

class EmoteManager(Cog):
    async def show_emotes(self, interaction: Interaction) -> None:
        """Shows all emoji's in one message."""
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
                    break
        else:
            if guild_counter < GUILD_OWNERSHIP_LIMIT:
                await self.bot.create_guild(name=f"{GUILD_NAME} {guild_counter}")
                guild_counter += 1
        await interaction.response.send_message("All available guilds and emoji's are filled.")




async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(EmoteManager(bot))  # type: ignore
