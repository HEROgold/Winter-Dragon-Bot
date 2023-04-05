
import logging
import os
import pickle

import discord
from discord import app_commands
from discord.ext import commands
import sqlalchemy

import config
from tools import app_command_tools, dragon_database_Sql

# TODO: https://docs.sqlalchemy.org/en/20/orm/quickstart.html

@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
class Welcome(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.DATABASE_NAME = self.__class__.__name__
        self.db = dragon_database_Sql.Database()
        self.setup_table()
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data = None
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def setup_table(self) -> None:
        self.logger.debug("Creating Table")
        with self.db.engine.connect() as connection:
            connection.execute
            connection.execute(sqlalchemy.text(f"""
            CREATE TABLE IF NOT EXISTS {self.DATABASE_NAME} (
                    guild_id INT(32) NOT NULL,
                    enabled BOOLEAN DEFAULT 0,
                    message CHAR(255),
                    PRIMARY KEY (guild_id)
            )
            ;
            """))

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member) -> None:
        with self.db.engine.connect() as connection:
            enabled, message = connection.execute(sqlalchemy.text(f"""
            SELECT (enabled, message) FROM {self.DATABASE_NAME} WHERE (guild_id={member.guild.id})
            """))
        if not enabled:
            return
        channel = member.guild.system_channel
        cmd = await app_command_tools.Converter(bot=self.bot).get_app_command(self.bot.get_command("help"))
        default_message = f"Welcome {member.mention} to {member.guild},\nyou may use {cmd.mention} to see what commands I have!"
        if channel is not None and config.Welcome.DM == False:
            self.logger.warning("sending welcome to guilds system_channel")
            if message:
                await channel.send(message)
            else:
                await channel.send(default_message)
        elif channel is not None and config.Welcome.DM == True and member.bot == False:
            self.logger.warning("sending welcome to user's dm")
            dm = member.dm_channel or await member.create_dm()
            if message:
                await dm.send(message)
            else:
                await dm.send(default_message)
        else:
            self.logger.warning("No system_channel to welcome user to, and dm is disabled.")

    @app_commands.command(
        name="enable",
        description="Enable welcome message",
    )
    async def slash_enable(self, interaction:discord.Interaction, message:str) -> None:
        with self.db.engine.connect() as connection:
            connection.execute(sqlalchemy.text(f"""
                REPLACE INTO {self.DATABASE_NAME} VALUES ({interaction.guild.id}, 0, 'Disabled.')
            """))
            connection.commit()
        await interaction.response.send_message("Enabled welcome message.", ephemeral=True)

    @app_commands.command(
        name="disable",
        description="Disable welcome message"
    )
    async def slash_disable(self, interaction:discord.Interaction) -> None:
        with self.db.engine.connect() as connection:
            connection.execute(sqlalchemy.text(f"""
                DELETE FROM {self.DATABASE_NAME} WHERE (guild_id={interaction.guild.id})
            """))
            connection.commit()
        await interaction.response.send_message("Disabled welcome message.", ephemeral=True)

async def setup(bot:commands.Bot) -> None:
    # sourcery skip: instance-method-first-arg-name
	await bot.add_cog(Welcome(bot))
