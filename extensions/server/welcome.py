import discord
from discord import app_commands

from tools.config_reader import config
from tools.database_tables import Welcome as WelcomeDb
from tools.database_tables import Session, engine
from _types.cogs import Cog, GroupCog
from _types.bot import WinterDragon


@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
class Welcome(GroupCog):
    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self.logger.debug(f"{member} joined {member.guild}")
        with Session(engine) as session:
            message = session.query(WelcomeDb).where(WelcomeDb.guild_id == member.guild.id).first().message
        channel = member.guild.system_channel
        cmd = self.bot.get_app_command("help")
        default_message = f"Welcome {member.mention} to {member.guild},\nyou may use {cmd.mention} to see what commands I have!"
        if channel is not None and config["Welcome"]["DM"] == False:
            self.logger.warning("sending welcome to guilds system_channel")
            if message:
                await channel.send(message)
            else:
                await channel.send(default_message)
        elif channel is not None and config["Welcome"]["DM"] == True and member.bot == False:
            self.logger.warning("sending welcome to user's dm")
            if message:
                await member.send(message)
            else:
                await member.send(default_message)
        else:
            self.logger.warning("No system_channel to welcome user to, and dm is disabled.")


    @app_commands.command(
        name="enable",
        description="Enable welcome message",
    )
    async def slash_enable(self, interaction: discord.Interaction) -> None:
        self.update_data(interaction, enabled=True)
        await interaction.response.send_message("Enabled welcome message.", ephemeral=True)


    @app_commands.command(
        name="disable",
        description="Disable welcome message"
    )
    async def slash_disable(self, interaction: discord.Interaction) -> None:
        self.update_data(interaction, enabled=False)
        await interaction.response.send_message("Disabled welcome message.", ephemeral=True)


    @app_commands.command(
        name="message",
        description="Change the welcome message",
    )
    async def slash_set_msg(self, interaction: discord.Interaction, message: str) -> None:
        self.update_data(interaction, message)
        await interaction.response.send_message(f"changed message to {message}")


    def update_data(
        self,
        interaction: discord.Interaction,
        message: str = None,
        enabled: bool = None,
        channel_id: int = None
    ) -> None:

        self.logger.debug(f"updating {WelcomeDb} for {interaction.guild} to {message=}, {enabled=}, {channel_id=}")
        if channel_id is None:
            channel_id = interaction.guild.system_channel.id

        with Session(engine) as session:
            data = session.query(WelcomeDb).get(interaction.guild.id)
            if enabled is None:
                enabled = data.enabled
            if message is None:
                message = data.message
            if data is None:
                session.add(WelcomeDb(
                    guild_id = interaction.guild.id,
                    channel_id = channel_id,
                    message = message,
                    enabled = enabled
                    ))
            else:
                data.channel_id = channel_id
                data.message = message
                data.enabled = enabled
            session.commit()


async def setup(bot: WinterDragon) -> None:
	await bot.add_cog(Welcome(bot))
