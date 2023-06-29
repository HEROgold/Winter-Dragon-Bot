import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config


class Sync(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    async def cog_load(self) -> None:
        self.update.start()


    # TODO: Extensive testing for edge cases
    @tasks.loop(count = 1)
    async def update(self) -> None:
        # sourcery skip: useless-else-on-loop
        app_commands = await self.bot.tree.fetch_commands()
        commands = list(self.bot.tree.walk_commands())
        synced = [
            cmd.name for cmd in commands
            for app_cmd in app_commands
            if app_cmd.name == cmd.name
            # or cmd.parent.name == app_cmd.name
        ]
        self.logger.debug(f"{synced=}")
        self.logger.debug(f"{[i.name for i in app_commands]=}")

        if not commands:
            self.logger.critical("No commands found")
            return
        if len(app_commands) == 0 or not synced:
            self.logger.warning("No synced commands found, automatically syncing")
            # await self.bot.tree.sync()
            return

        # goal: for each app_command thats found, but not in commands, == de-synced
        # goal: for each command not in app_commands == de-synced
        for app_command in app_commands:
            self.logger.debug(f"checking {app_command.name}")
            for command in commands:
                if command.parent is not None:
                    continue
                if command.name == app_command.name:
                    self.logger.debug(f"cmd.name in app_cmd: {app_command.name=}, {command.name=}")
                    break
            else:
                self.logger.debug(f"cmd.name not in app_cmd: {app_command.name=}, {command.name=}")
                break
            continue
        else:
            return
        self.logger.warning("De-sync found, re-syncing")
        # await self.bot.tree.sync()


    @update.before_loop # type: ignore
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @app_commands.guilds(config.Main.SUPPORT_GUILD_ID)
    @app_commands.command(name="sync", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync(self, interaction: discord.Interaction) -> None:
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        global_sync = await self.bot.tree.sync()
        guild = self.bot.get_guild(config.Main.SUPPORT_GUILD_ID)
        local_sync = await self.bot.tree.sync(guild=guild)
        self.logger.warning(f"{interaction.user} Synced slash commands!")
        self.logger.debug(f"Synced commands: global_commands={global_sync} guild_commands={local_sync}")
        global_list = [command.name for command in global_sync]
        local_list = [command.name for command in local_sync]
        global_list.sort()
        local_list.sort()
        await interaction.response.send_message(f"Sync complete\nGlobally synced: {global_list}\nLocally synced: {local_list} to {guild}", ephemeral=True)


    @commands.hybrid_command(name="sync_ctx", description="Sync all commands on all servers (Bot dev only)")
    async def slash_sync_hybrid(self, ctx: commands.Context) -> None:
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner
        global_sync = await self.bot.tree.sync()
        guild = self.bot.get_guild(config.Main.SUPPORT_GUILD_ID)
        local_sync = await self.bot.tree.sync(guild=guild)
        self.logger.warning(f"{ctx.author} Synced slash commands!")
        self.logger.debug(f"Synced commands: global_commands={global_sync} guild_commands={local_sync}")
        global_list = [command.name for command in global_sync]
        local_list = [command.name for command in local_sync]
        global_list.sort()
        local_list.sort()
        await ctx.send(f"Sync complete\nGlobally synced: {global_list}\nLocally synced: {local_list} to {guild}")



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sync(bot))