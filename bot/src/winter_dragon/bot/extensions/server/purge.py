"""A cog that provides a command to purge messages."""

import contextlib

import discord
from discord import app_commands
from winter_dragon.bot.config import Config, config
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import Cog


@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
class Purge(Cog):
    """A cog that provides a command to purge messages."""

    limit = Config(100)
    use_history = Config(False)  # noqa: FBT003

    @app_commands.command(name="purge", description="Purge X amount of messages, use history to delete older messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def slash_purge(
        self,
        interaction: discord.Interaction,
        count: int,
        *,
        use_history: bool = False,
    ) -> None:
        """Purge X amount of messages, use history to delete older messages."""
        purge_limit = config.getint("Purge", "limit")
        if count == -1:
            count = purge_limit
        if count <= purge_limit:
            await interaction.response.defer()
            history_messages_count = 0
            purged_count = 0
            purged = await interaction.channel.purge(limit=count)
            purged_count = len(purged)
            self.logger.debug(f"Purged: {purged_count}")
            use_history_config = config.getboolean("Purge", "use_history")
            if (
                purged_count < count
                and use_history_config
                and use_history
            ):
                history_messages = await self.history_delete(interaction=interaction, count=(count - purged_count))
                history_messages_count = len(history_messages)
                self.logger.debug(f"History killed: {history_messages_count}")
            await interaction.followup.send(
                f"{interaction.user.mention} Killed {history_messages_count + purged_count} Messages",
            )
        else:
            await interaction.response.send_message(
                f"Too many message to kill! The limit is {config['Purge']['LIMIT']}",
                ephemeral=True,
            )


    async def history_delete(self, interaction: discord.Interaction, count: int) -> list[discord.Message]:
        """Delete messages from the channel history. Rather than messages in cache. (Older messages)."""
        messages = []
        async for message in interaction.channel.history(limit=count):
            message: discord.Message
            with contextlib.suppress(discord.NotFound):
                await message.delete()
            messages.append(message)
        return messages


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Purge(bot))
