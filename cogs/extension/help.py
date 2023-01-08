import logging
import random
from math import ceil

import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands

import config
import rainbow


class Help(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.logger = logging.getLogger("winter_dragon.help")

    async def CreateButton(self, label:str, style:discord.ButtonStyle):
        return Button(label=label, style=style)

    async def CreateHelpEmbed(self, HelpInput:str|int, commands_list:list[app_commands.Command]|list[commands.Command]) -> discord.Embed|discord.ui.View:
        if isinstance(HelpInput, str):
            embed = discord.Embed(title=f"Command {HelpInput}", color=random.choice(rainbow.RAINBOW))
            for command in commands_list:
                embed = self.PopulateCommandEmbed(HelpInput, embed, command)
            return embed
        elif isinstance(HelpInput, int):
            page_number = HelpInput
        else:
            self.logger.warning("HelpInput is not str or int.")
            return None
        embed = discord.Embed(title=f"Help page {page_number}", description="Description and explanation of all commands", color=0xffaf00)
        for i, command in enumerate(commands_list):
            if not HelpInput:
                min_per_page = 0
                max_per_page = config.help.max_per_page
            elif isinstance(HelpInput, int):
                min_per_page = ((HelpInput * config.help.max_per_page) - config.help.max_per_page)
                max_per_page = min_per_page + config.help.max_per_page
            if i > min_per_page and i <= max_per_page:
                embed.add_field(name=command.name, value=command.description, inline=True)
            elif i <= max_per_page:
                last_page = ceil((i+1)/config.help.max_per_page)
                embed.set_footer(text=f"No more commands to display. Last page is: Help {last_page}")
            else:
                embed.set_footer(text=f"More commands on other pages. Try: Help {page_number+1}")
                continue
        view = await self.ButtonHandler(HelpInput, commands_list, View())
        return embed, view

    # FIXME: Pages work, single command's don't
    # 2023-01-08 05:31:58,972:ERROR:winter_dragon.error: Command 'help' raised an exception: TypeError: cannot unpack non-iterable Embed object
    # Traceback (most recent call last):
    #   File "C:\Users\marti\AppData\Local\Packages\discord\app_commands\commands.py", line 861, in _do_call
    #     return await self._callback(self.binding, interaction, **params)  # type: ignore
    #   File "c:\Users\marti\Documents\GitHub\Winter-Dragon-Bot\cogs\extension\help.py", line 91, in slash_help
    #     embed, view = await self.CreateHelpEmbed(HelpInput=query, commands_list=commands)
    # TypeError: cannot unpack non-iterable Embed object
    # 
    # The above exception was the direct cause of the following exception:
    # 
    # Traceback (most recent call last):
    #   File "C:\Users\marti\AppData\Local\Packages\discord\app_commands\tree.py", line 1242, in _call
    #     await command._invoke_with_namespace(interaction, namespace)
    #   File "C:\Users\marti\AppData\Local\Packages\discord\app_commands\commands.py", line 887, in _invoke_with_namespace
    #     return await self._do_call(interaction, transformed_values)
    #   File "C:\Users\marti\AppData\Local\Packages\discord\app_commands\commands.py", line 876, in _do_call
    #     raise CommandInvokeError(self, e) from e
    # discord.app_commands.errors.CommandInvokeError: Command 'help' raised an exception: TypeError: cannot unpack non-iterable Embed object
    def PopulateCommandEmbed(self, HelpInput:str, embed:discord.Embed, command:commands.Command|app_commands.Command) -> discord.Embed:
        self.logger.debug(f"Target command: {HelpInput}")
        if isinstance(command, commands.Command):
            command:commands.Command
            self.logger.debug(f"from commands.Command: {command.name}")
            if command.name == HelpInput:
                self.logger.debug(command.name, command.brief, command.description, command.usage)
                embed.add_field(name="Brief", value=command.brief, inline=False)
                embed.add_field(name="Description", value=command.description, inline=False)
                embed.add_field(name="Usage", value=command.usage, inline=False)
        elif isinstance(command, app_commands.Command):
            self.logger.debug(f"from app_commands.Command: {command.name}")
            command:app_commands.Command
            if command.name == HelpInput:
                self.logger.debug(command.name, command.description)
                embed.add_field(name="Description", value=command.description, inline=False)
        return embed

    async def UpdateView(self, view:discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view

    # TODO: rewrite help for slash commands WITH buttons
    @app_commands.command(
        name="help",
        description="Get information about commands!"
    )
    @app_commands.checks.cooldown(1, 10)
    async def slash_help(self, interaction:discord.Interaction, page:int=None, command:str=None):
        if page is None and command is None and not (page and command):
            await interaction.response.send_message("Give me either a page number or command for more information. Not both, and not none", ephemeral=True)
            return
        else:
            query = page or command
        commands = self.bot.tree.get_commands()
        command_names = [i.name for i in commands]
        self.logger.debug(command_names)
        embed, view = await self.CreateHelpEmbed(HelpInput=query, commands_list=commands)
        await interaction.response.send_message(embed=embed, view=view)

    @slash_help.autocomplete("command")
    async def autocomplete_help(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        commands = self.bot.tree.get_commands()
        command_names = [command.name for command in commands]
        return [
            app_commands.Choice(name=commands, value=commands)
            for commands in command_names
            if current.lower() in commands.lower()
        ]

    # TODO: rewrite help for slash commands WITH buttons
    @commands.command(description = "Use this command to get information about all available commands.",
                    brief = "Sends this help page!",
                    usage = "help [page or command]:\nExample:`help 1`, `help invite`")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def help(self, ctx:commands.Context, HelpInput):
        # sourcery skip: de-morgan, useless-else-on-loop
        # 3 types of commands, Chat, Slash (/) And all.
        # all_list = self.bot.all_commands # Command raised an exception: AttributeError: 'str' object has no attribute 'name'
        # slash_list = self.bot.application_commands # Command raised an exception: AttributeError: 'str' object has no attribute 'name'
        commands_list = self.bot.commands
        if HelpInput is None:
            HelpInput = 1
        try:
            HelpInput = int(HelpInput)
            if HelpInput <= 0:
                await ctx.send("The page number cannot be 0 or less then 0.")
                return
        except Exception as e:
            self.logger.error(f"Help.py: {e}")
        embed, view = await self.CreateHelpEmbed(HelpInput=HelpInput, commands_list=commands_list)
        await ctx.send(embed=embed, view=view)

    async def ButtonHandler(self, HelpInput:int, commands_list, view:discord.ui.View) -> discord.ui.View:
        ButtonLeft = await self.CreateButton(label=f"Help {HelpInput-1}", style=discord.ButtonStyle.primary)
        ButtonRight = await self.CreateButton(label=f"Help {HelpInput+1}", style=discord.ButtonStyle.primary)
    # Defines functions inside ButtonHandler because each button needs their own.
        async def ButtonAction(interaction:discord.Interaction, HelpInput):
            embed, view = await self.CreateHelpEmbed(HelpInput=HelpInput, commands_list=commands_list)
            ButtonLeft.label = f"Help {HelpInput-1}"
            ButtonRight.label = f"Help {HelpInput+1}"
            MoreThenMax = (HelpInput * config.help.max_per_page) >= len(commands_list)
            self.logger.debug(f"Checking HelpInput values: {HelpInput}")
            if HelpInput > 1 and not MoreThenMax:
                NewView = await self.UpdateView(view, ButtonLeft, ButtonRight)
            elif HelpInput <= 1:
                NewView = await self.UpdateView(view, ButtonRight)
            elif MoreThenMax:
                NewView = await self.UpdateView(view, ButtonLeft)
            self.logger.debug("Editing original message")
            try:
                await interaction.response.edit_message(embed=embed, view=NewView)
            except Exception as e:
                self.logger.exception(e)
                await interaction.followup.edit_message(embed=embed, view=NewView)
            self.logger.debug("Edited original message")

        self.logger.debug("Defining Left Button action")
        async def ButtonLeftAction(interaction:discord.Interaction):
            nonlocal HelpInput
            HelpInput -= 1
            await ButtonAction(interaction, HelpInput)

        self.logger.debug("Defining Right Button action")
        async def ButtonRightAction(interaction:discord.Interaction):
            nonlocal HelpInput
            HelpInput += 1
            await ButtonAction(interaction, HelpInput)

        self.logger.debug("Adding callback and buttons to view")
        ButtonLeft.callback = ButtonLeftAction
        ButtonRight.callback = ButtonRightAction
        view.add_item(ButtonLeft)
        view.add_item(ButtonRight)
        if HelpInput <= 1:
            view.remove_item(ButtonLeft)
            self.logger.debug("Removing button left")
        self.logger.debug(f"Returning view: {view}")
        return view
    # End ButtonHandler

async def setup(bot:commands.Bot):
    await bot.add_cog(Help(bot))