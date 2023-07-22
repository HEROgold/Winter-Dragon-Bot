import logging
import random
from math import ceil
from typing import overload

import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands

from tools.config_reader import config
import rainbow


# TODO: Rewrite/cleanup
class Help(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")


    @overload
    async def CreateHelpEmbed(
        self,
        help_input: str,
        commands_list: list[app_commands.AppCommand] | list[commands.Command],
    ) -> discord.Embed | discord.ui.View:
        ...

    @overload
    async def CreateHelpEmbed(
        self,
        help_input: int,
        commands_list: list[app_commands.AppCommand] | list[commands.Command],
    ) -> discord.Embed | discord.ui.View:
        ...

    async def CreateHelpEmbed(
        self,
        help_input: int | str,
        commands_list: list[app_commands.AppCommand] | list[commands.Command],
    ) -> discord.Embed | discord.ui.View:
        if type(help_input) ==  str:
            embed = discord.Embed(title=f"Command {help_input}", color=random.choice(rainbow.RAINBOW))
            for command in commands_list:
                embed = self.PopulateCommandEmbed(help_input, embed, command)
            return embed, None
        elif type(help_input) == int:
            page_number = help_input
            embed = discord.Embed(
                title=f"Help page {page_number}",
                description="Description and explanation of all commands",
                color=random.choice(rainbow.RAINBOW),)

            min_per_page = help_input * config.Help.PAGE_MAX - config.Help.PAGE_MAX
            max_per_page = min_per_page + config.Help.PAGE_MAX

            for i, command in enumerate(commands_list):
                if i > min_per_page and i <= max_per_page:
                    embed.add_field(name=command.name, value=command.description, inline=True)
                elif i <= max_per_page:
                    last_page = ceil((i + 1) / config.Help.PAGE_MAX)
                    embed.set_footer(text=f"No more commands to display. Last page is: Help {last_page}")
                else:
                    embed.set_footer(text=f"More commands on other pages. Try: Help {page_number+1}")
                    continue
            view = await self.ButtonHandler(help_input, commands_list, View())
            return embed, view


    @overload
    def PopulateCommandEmbed(
        self, help_input: str, embed: discord.Embed, command: commands.Command
    ) -> discord.Embed:
        ...

    @overload
    def PopulateCommandEmbed(
        self, help_input: str, embed: discord.Embed, command: app_commands.AppCommand
    ) -> discord.Embed:
        ...

    def PopulateCommandEmbed(
        self,
        help_input: str,
        embed: discord.Embed,
        command: app_commands.AppCommand | commands.Command
    ) -> discord.Embed:
        if command == commands.Command:
            if command.name == help_input:
                self.logger.debug(f"{command.name}, {command.description}")
                embed.add_field(name="Description", value=command.description, inline=False)
                embed.add_field(name="Example use", value=command.mention, inline=False)
            return embed
        if command == app_commands.AppCommand and command.name == help_input:
            self.logger.debug(command.name, command.brief, command.description, command.usage)
            embed.add_field(name="Brief", value=command.brief, inline=False)
            embed.add_field(name="Description", value=command.description, inline=False)
            embed.add_field(name="Usage", value=command.usage, inline=False)
        return embed


    async def UpdateView(self, view:discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view


    @app_commands.command(name="help", description="Get information about commands!")
    @app_commands.checks.cooldown(1, 5)
    async def slash_help(
        self,
        interaction: discord.Interaction,
        page: int = None, command: str = None
    ) -> None:
        if page and page <= 0:
            await interaction.response.send_message("Page has to be 1 or bigger", ephemeral=True)
            return
        if not (bool(page) ^ bool(command)):
            await interaction.response.send_message(
                "Give me either a page number or command for more information. Not both, and not none",
                ephemeral=True,
            )
            return
    
        query = page or command
        commands = self.bot.tree.get_commands() or await self.bot.tree.fetch_commands()
        embed, view = await self.CreateHelpEmbed(help_input=query, commands_list=commands)
        if view is None:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @slash_help.autocomplete("command")
    async def autocomplete_help(self, interaction:discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        commands = self.bot.tree.get_commands()
        command_names = [command.name for command in commands]
        return [
            app_commands.Choice(name=commands, value=commands)
            for commands in command_names
            if current.lower() in commands.lower()
        ] or [
            app_commands.Choice(name=commands, value=commands)
            for commands in command_names
        ]


    @commands.cooldown(1, 2, commands.BucketType.member)
    @commands.command(
            description = "Use this command to get information about all available commands.",
            brief = "Sends this help page!",
            usage = "help [page or command]:\nExample:`help 1`, `help invite`"
            )
    async def help(self, ctx:commands.Context, help_input) -> None:
        commands_list = self.bot.commands
        if help_input is None:
            help_input = 1
        help_input = int(help_input)
        if help_input <= 0:
            await ctx.send("The page number cannot be 0 or less then 0.")
            return
        embed, view = await self.CreateHelpEmbed(help_input=help_input, commands_list=commands_list)
        await ctx.send(embed=embed, view=view)


    async def ButtonHandler(self, help_input:int, commands_list:list[app_commands.Command]|list[commands.Command], view:discord.ui.View) -> discord.ui.View:
        """Function to handle views, can update or create view.

        Args:
            HelpInput (int): Page number of which to create buttons
            commands_list: List of command objects, can either be discord app_commands.Command or commands.Command
            view: discord.ui.View

        Returns:
            discord.ui.View
        """
        button_left = Button(label=f"Help {help_input-1}", style=discord.ButtonStyle.primary)
        button_right = Button(label=f"Help {help_input+1}", style=discord.ButtonStyle.primary)

    # Defines functions inside ButtonHandler because each button needs their own.
        async def button_action(interaction:discord.Interaction, help_input:int) -> None:
            embed, view = await self.CreateHelpEmbed(help_input=help_input, commands_list=commands_list)
            button_left.label = f"Help {help_input-1}"
            button_right.label = f"Help {help_input+1}"
            more_than_max = (help_input * config.Help.PAGE_MAX) >= len(commands_list)
            self.logger.debug(f"Checking HelpInput values: {help_input}")
            if help_input > 1 and not more_than_max:
                new_view = await self.UpdateView(view, button_left, button_right)
            elif help_input <= 1:
                new_view = await self.UpdateView(view, button_right)
            elif more_than_max:
                new_view = await self.UpdateView(view, button_left)
            else:
                self.logger.debug("NewView Else Escape")
            self.logger.debug("Editing original help message")
            try:
                await interaction.response.edit_message(embed=embed, view=new_view)
            except discord.errors.InteractionResponded as e:
                self.logger.warning(f"Could not send response, sending followup instead: {e}")
                await interaction.followup.edit_message(embed=embed, view=new_view)

        self.logger.debug("Defining Left Button action")
        async def button_action_left(interaction:discord.Interaction) -> None:
            nonlocal help_input
            help_input -= 1
            await button_action(interaction, help_input)

        self.logger.debug("Defining Right Button action")
        async def button_action_right(interaction:discord.Interaction) -> None:
            nonlocal help_input
            help_input += 1
            await button_action(interaction, help_input)

        self.logger.debug("Adding callback and buttons to view")
        button_left.callback = button_action_left
        button_right.callback = button_action_right
        view.add_item(button_left)
        view.add_item(button_right)
        if help_input <= 1:
            view.remove_item(button_left)
            self.logger.debug("Removing button left")
        self.logger.debug(f"Returning view: {view}")
        return view


# TODO: get code underneath to work.
# Then inplement in own help cmd.
class HelpView(discord.ui.View):
    def __init__(
        self,
        parent_embed: discord.Embed,
        group_list: list[app_commands.commands.Group],
        **kwargs
    ) -> None:
        self.embed = parent_embed
        super().__init__(**kwargs)
        self.add_item(Dropdown(group_list))

    @discord.ui.button(label="Back", emoji="⬅️", style=discord.ButtonStyle.secondary, row=1)
    async def backbutton(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=self.embed)

class CopiedDropdownHelp(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")

    # @app_commands.describe(group = "The specific group you want help on.")
    @app_commands.command(name="helpcopied", description="Gives a brief description of all features.")
    async def slash_help(
        self,
        interaction: discord.Interaction
    ) -> None:
        embed = discord.Embed(
            title="Help Desk",
            description="Select the specific feature from the dropdown for additional details",
            color=discord.Colour.brand_green()
        )
        group_list = []
        for command in app_commands.CommandTree.walk_commands(self.bot.tree):
            if isinstance(command, app_commands.commands.Group):
                group_list.append(command)
                embed.add_field(
                    name=command.description,
                    value=f"`/{command.name}`"
                )
        await interaction.response.send_message(embed=embed, view=HelpView(embed, group_list), ephemeral=True)


class Dropdown(discord.ui.Select):
    def __init__(self, group_list: list[app_commands.commands.Group]) -> None:
        self.groupList = group_list
        options = [discord.SelectOption(
            label=group.description, description=f"/{group.name}") for group in group_list]
        super().__init__(placeholder="Select which feature to get help for.", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        group_name = self.values[0]
        command_list_embed = discord.Embed(
            title=f"{group_name}",
            color=discord.Colour.brand_green()
        )
        for group in self.groupList:
            if group.description == group_name:
                for command in group.commands:
                    if command == app_commands.commands.Command:
                        command_list_embed.add_field(name=f"/{group.name} {command.name}", value=command.description, inline=False)
                break
        await interaction.response.edit_message(embed=command_list_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
    # await bot.add_cog(CopiedDropdownHelp(bot))
