import logging
import random
from math import ceil

import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands

import config
import rainbow

# TODO: Rewrite/cleanup
class Help(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    async def CreateHelpEmbed(self, HelpInput:str|int, commands_list:list[app_commands.AppCommand]|list[commands.Command]) -> discord.Embed|discord.ui.View:
        if isinstance(HelpInput, str):
            embed = discord.Embed(title=f"Command {HelpInput}", color=random.choice(rainbow.RAINBOW))
            for command in commands_list:
                embed = self.PopulateCommandEmbed(HelpInput, embed, command)
            return embed, None
        else:
            page_number = HelpInput
            embed = discord.Embed(title=f"Help page {page_number}", description="Description and explanation of all commands", color=random.choice(rainbow.RAINBOW))
            for i, command in enumerate(commands_list):
                min_per_page = ((HelpInput * config.Help.PAGE_MAX) - config.Help.PAGE_MAX)
                max_per_page = min_per_page + config.Help.PAGE_MAX
                if i > min_per_page and i <= max_per_page:
                    embed.add_field(name=command.name, value=command.description, inline=True)
                elif i <= max_per_page:
                    last_page = ceil((i+1)/config.Help.PAGE_MAX)
                    embed.set_footer(text=f"No more commands to display. Last page is: Help {last_page}")
                else:
                    embed.set_footer(text=f"More commands on other pages. Try: Help {page_number+1}")
                    continue
            view = await self.ButtonHandler(HelpInput, commands_list, View())
            return embed, view

    def PopulateCommandEmbed(self, HelpInput:str, embed:discord.Embed, command:commands.Command|app_commands.AppCommand) -> discord.Embed:
        # self.logger.debug(f"Target command: {HelpInput}")
        if isinstance(command, commands.Command):
            command:commands.Command
            # self.logger.debug(f"from commands.Command (text): {command.name}")
            if command.name == HelpInput:
                self.logger.debug(command.name, command.brief, command.description, command.usage)
                embed.add_field(name="Brief", value=command.brief, inline=False)
                embed.add_field(name="Description", value=command.description, inline=False)
                embed.add_field(name="Usage", value=command.usage, inline=False)
        else:
            command:app_commands.AppCommand
            # self.logger.debug(f"from app_commands.AppCommand (slash): {command.name}")
            if command.name == HelpInput:
                self.logger.debug(f"{command.name}, {command.description}")
                embed.add_field(name="Description", value=command.description, inline=False)
                embed.add_field(name="Exapmle use", value=command.mention, inline=False)
        return embed

    async def UpdateView(self, view:discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view

    @app_commands.command(
        name="help",
        description="Get information about commands!"
    )
    @app_commands.checks.cooldown(1, 5)
    async def slash_help(self, interaction:discord.Interaction, page:int=None, command:str=None) -> None:
        if page and page <= 0:
            await interaction.response.send_message("Page has to be 1 or bigger")
            return
        if not (bool(page) ^ bool(command)):
            await interaction.response.send_message("Give me either a page number or command for more information. Not both, and not none", ephemeral=True)
            return
        else:
            query = page or command
        # commands = self.bot.tree.get_commands()
        commands = await self.bot.tree.fetch_commands()
        embed, view = await self.CreateHelpEmbed(HelpInput=query, commands_list=commands)
        if view is None:
            await interaction.response.send_message(embed=embed)
        else:
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

    @commands.command(description = "Use this command to get information about all available commands.",
                    brief = "Sends this help page!",
                    usage = "help [page or command]:\nExample:`help 1`, `help invite`")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def help(self, ctx:commands.Context, HelpInput) -> None:
        commands_list = self.bot.commands
        if HelpInput is None:
            HelpInput = 1
        HelpInput = int(HelpInput)
        if HelpInput <= 0:
            await ctx.send("The page number cannot be 0 or less then 0.")
            return
        embed, view = await self.CreateHelpEmbed(HelpInput=HelpInput, commands_list=commands_list)
        await ctx.send(embed=embed, view=view)

    async def ButtonHandler(self, HelpInput:int, commands_list:list[app_commands.Command]|list[commands.Command], view:discord.ui.View) -> discord.ui.View:
        """Function to handle views, can update or create view.

        Args:
            HelpInput (int): Page number of which to create buttons
            commands_list: List of command objects, can either be discord app_commands.Command or commands.Command
            view: discord.ui.View

        Returns:
            discord.ui.View
        """
        ButtonLeft = Button(label=f"Help {HelpInput-1}", style=discord.ButtonStyle.primary)
        ButtonRight = Button(label=f"Help {HelpInput+1}", style=discord.ButtonStyle.primary)
    # Defines functions inside ButtonHandler because each button needs their own.
        async def ButtonAction(interaction:discord.Interaction, HelpInput:int) -> None:
            embed, view = await self.CreateHelpEmbed(HelpInput=HelpInput, commands_list=commands_list)
            ButtonLeft.label = f"Help {HelpInput-1}"
            ButtonRight.label = f"Help {HelpInput+1}"
            MoreThenMax = (HelpInput * config.Help.PAGE_MAX) >= len(commands_list)
            self.logger.debug(f"Checking HelpInput values: {HelpInput}")
            if HelpInput > 1 and not MoreThenMax:
                NewView = await self.UpdateView(view, ButtonLeft, ButtonRight)
            elif HelpInput <= 1:
                NewView = await self.UpdateView(view, ButtonRight)
            elif MoreThenMax:
                NewView = await self.UpdateView(view, ButtonLeft)
            else:
                self.logger.debug("NewView Else Escape")
            self.logger.debug("Editing original help message")
            try:
                await interaction.response.edit_message(embed=embed, view=NewView)
            except discord.errors.InteractionResponded as e:
                self.logger.warning(f"Could not send response, sending followup instead: {e}")
                await interaction.followup.edit_message(embed=embed, view=NewView)

        self.logger.debug("Defining Left Button action")
        async def ButtonLeftAction(interaction:discord.Interaction) -> None:
            nonlocal HelpInput
            HelpInput -= 1
            await ButtonAction(interaction, HelpInput)

        self.logger.debug("Defining Right Button action")
        async def ButtonRightAction(interaction:discord.Interaction) -> None:
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

async def setup(bot:commands.Bot) -> None:
    await bot.add_cog(Help(bot))