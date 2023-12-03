"""
Allow admins to enable/disable certain commands,
also allow them to sync commands to their guild 
so that disabled commands don't show up

Ratelimit the sync for a guild to once per day

Get and store enabled commands per guild in database
"""

from typing import Any
import discord
from discord import app_commands
from discord.app_commands import Command as DcCommand

from _types.cogs import GroupCog #, Cog
from _types.bot import WinterDragon
from tools.database_tables import Session, engine, Command as DbCommand, GuildCommands, CommandGroup


# TODO: test
# TODO: allow command groups to be disabled
# TODO: add and manage commands / command groups > Database
class CombinedCommand:
    dc_command: DcCommand
    db_command: DbCommand

    def __init__(self, dc_command: DcCommand) -> None:
        self.dc_command = dc_command
        with Session(engine) as engine:
            self.db_command = engine.query(DbCommand).where(DbCommand.qual_name == dc_command.qualified_name).first()


class CommandControl(GroupCog):
    commands: list[DbCommand | CommandGroup]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        with Session(engine) as session:
            self.commands = session.query(DbCommand).all()
            self.commands += session.query(CommandGroup).all()


    @app_commands.command(name="enable", description="Enable a command")
    async def slash_command_enable(self, interaction: discord.Interaction, command: str) -> None:
        """CommandControl"""
        with Session(engine) as session:
            cmd = session.query(DbCommand).where(DbCommand.qual_name == command).first()
            group = session.query(CommandGroup).where(CommandGroup.name == command).first()
            session.add(GuildCommands(
                guild_id = interaction.guild.id,
                command_id = cmd.id
            ))
            session.commit()
        await interaction.response.send_message(f"Enabled {cmd.qual_name}")


    @app_commands.command(name="disable", description="Disable a command")
    async def slash_command_disable(self, interaction: discord.Interaction, command: str) -> None:
        """CommandControl"""
        with Session(engine) as session:
            cmd = session.query(GuildCommands).join(DbCommand).where(DbCommand.qual_name == command).first()
            self.logger.debug(f"{cmd}")
            session.delete(cmd)
            session.commit()
        await interaction.response.send_message(f"Disabled {command}")


    @slash_command_enable.autocomplete("command")
    @slash_command_disable.autocomplete("command")
    async def activity_autocomplete_status(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=command.qual_name, value=command.qual_name)
            for command in self.commands
            if current.lower() in command.qual_name.lower()
        ] or [
            app_commands.Choice(name=command.qual_name, value=command.qual_name)
            for i, command in enumerate(self.commands)
            if i < 25
        ]


async def setup(bot: WinterDragon) -> None:
    return
    await bot.add_cog(CommandControl(bot))

# Ai example code for inspiration

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
