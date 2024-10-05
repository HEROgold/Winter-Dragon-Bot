"""
Allow admins to enable/disable certain commands,
also allow them to sync commands to their guild
so that disabled commands don't show up

Ratelimit the sync for a guild to once per day

Get and store enabled commands per guild in database
"""


import discord
from discord import app_commands
from discord.app_commands import Command as DcCommand
from sqlalchemy.orm import Session

from bot import WinterDragon
from bot._types.cogs import GroupCog  #, Cog
from database import engine
from database.tables import Command as DbCommand
from database.tables import CommandGroup, GuildCommands


# TODO: test
# TODO: allow command groups to be disabled
# TODO: add and manage commands / command groups > Database
class CombinedCommand:
    dc_command: DcCommand
    db_command: DbCommand

    def __init__(self, dc_command: DcCommand) -> None:
        self.dc_command = dc_command
        with Session(engine) as session:
            self.db_command = session.query(DbCommand).where(DbCommand.qual_name == dc_command.qualified_name).first()


class CommandControl(GroupCog):
    commands: list[DbCommand | CommandGroup]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        with self.session as session:
            self.commands = session.query(DbCommand).all()
            self.commands += session.query(CommandGroup).all()


    @app_commands.command(name="enable", description="Enable a command")
    async def slash_command_enable(self, interaction: discord.Interaction, command: str) -> None:
        """CommandControl"""
        with self.session as session:
            cmd = session.query(DbCommand).where(DbCommand.qual_name == command).first()
            session.query(CommandGroup).where(CommandGroup.name == command).first()
            session.add(GuildCommands(
                guild_id = interaction.guild.id,
                command_id = cmd.id,
            ))
            session.commit()
        await interaction.response.send_message(f"Enabled {cmd.qual_name}")


    @app_commands.command(name="disable", description="Disable a command")
    async def slash_command_disable(self, interaction: discord.Interaction, command: str) -> None:
        """CommandControl"""
        with self.session as session:
            cmd = session.query(GuildCommands).join(DbCommand).where(DbCommand.qual_name == command).first()
            self.logger.debug(f"{cmd}")
            session.delete(cmd)
            session.commit()
        await interaction.response.send_message(f"Disabled {command}")


    @slash_command_enable.autocomplete("command")
    @slash_command_disable.autocomplete("command")
    async def activity_autocomplete_status(
        self, interaction: discord.Interaction, current: str,
    ) -> list[app_commands.Choice[str]]:
        choice_limit = 25
        return [
            app_commands.Choice(name=command.qual_name, value=command.qual_name)
            for command in self.commands
            if current.lower() in command.qual_name.lower()
        ] or [
            app_commands.Choice(name=command.qual_name, value=command.qual_name)
            for i, command in enumerate(self.commands)
            if i < choice_limit
        ]


async def setup(bot: WinterDragon) -> None:
    return
    await bot.add_cog(CommandControl(bot))

# Ai example code for inspiration AI1

# from sqlalchemy import create_engine, Column, Integer, String, Boolean
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()

# class CommandControl(Base):
#     __tablename__ = 'command_control'

#     id = Column(Integer, primary_key=True)
#     guild_id = Column(Integer)
#     command_name = Column(String)
#     enabled = Column(Boolean)

#     def __init__(self, guild_id, command_name, enabled):
#         self.guild_id = guild_id
#         self.command_name = command_name
#         self.enabled = enabled

# # Create the database engine and session
# engine = create_engine('sqlite:///command_control.db')
# Session = sessionmaker(bind=engine)


# class CombinedCommand:
#     dc_command: DcCommand
#     db_command: DbCommand

#     def __init__(self, dc_command: DcCommand) -> None:
#         self.dc_command = dc_command
#         with Session() as session:
#             db_command = session.query(CommandControl).filter_by(guild_id=guild_id, command_name=dc_command.qualified_name).first()
#             if db_command and not db_command.enabled:
#                 self.dc_command.enabled = False


# @bot.command()
# async def my_command(ctx):
#     guild_id = ctx.guild.id
#     command_name = "my_command"

#     with Session() as session:
#         db_command = session.query(CommandControl).filter_by(guild_id=guild_id, command_name=command_name).first()
#         if db_command and not db_command.enabled:
#             await ctx.send("This command is disabled for this guild.")
#             return

#     # Command logic goes here




# You.com Code ai inspiration AI2

# import discord
# from discord.ext import commands

# Assume you have a database connection and cursor already established

# # Function to check if a command is enabled for a guild
# def is_command_enabled(server_id, command_name):
#     # Query the Commands Table to check if the command is enabled for the guild
#     # Return True if enabled, False if disabled

# # Function to check if a subcommand is enabled for a guild
# def is_subcommand_enabled(server_id, parent_command, subcommand):
#     # Query the Commands Table to check if the subcommand is enabled for the guild
#     # Return True if enabled, False if disabled

# # Your bot code
# bot = commands.Bot(command_prefix='!')

# @bot.command()
# async def greet(ctx):
#     if is_command_enabled(ctx.guild.id, "greet"):
#         await ctx.send('Hello!')

# @bot.group()
# async def music(ctx):
#     pass

# @music.command()
# async def play(ctx):
#     if is_subcommand_enabled(ctx.guild.id, "music", "play"):
#         # Play music logic
#     else:
#         await ctx.send('The play command is disabled.')

# # Other commands and subcommands follow the same pattern

# bot.run('your_token')
