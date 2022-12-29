import logging
from math import ceil
import discord
import config
from discord.ext import commands
from discord.ui import Button, View
import random
import rainbow

class Help(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot

    async def CreateButton(self, label:str, style:discord.ButtonStyle):
        return Button(label=label, style=style)

    async def CreateHelpEmbed(self, HelpInput, chat_list) -> discord.Embed:
        if HelpInput is not None and not isinstance(HelpInput, int):
            if not isinstance(HelpInput, str):
                return
            for command in chat_list:
                if str(command) == HelpInput:
                    embed = discord.Embed(title=f"Command {HelpInput}", color=random.choice(rainbow.RAINBOW))
                    embed.add_field(name="Brief", value=command.brief, inline=False)
                    embed.add_field(name="Description", value=command.description, inline=False)
                    embed.add_field(name="Usage", value=command.usage, inline=False)
            return embed
        elif isinstance(HelpInput, int):
            page_number = HelpInput
        embed = discord.Embed(title=f"Help page {page_number}", description="Description and explanation of all commands", color=0xffaf00)
        for i, command in enumerate(chat_list):
            if not HelpInput:
                min_per_page = 0
                max_per_page = config.help.max_per_page
            elif isinstance(HelpInput, int):
                min_per_page = ((HelpInput * config.help.max_per_page) - config.help.max_per_page)
                max_per_page = min_per_page + config.help.max_per_page
            if i > min_per_page and i <= max_per_page:
                embed.add_field(name=command.name, value=command.brief, inline=True)
            elif i <= max_per_page:
                last_page = ceil((i+1)/config.help.max_per_page)
                embed.set_footer(text=f"No more commands to display. Last page is: Help {last_page}")
            else:
                embed.set_footer(text=f"More commands on other pages. Try: Help {page_number+1}")
                continue
        return embed

    async def UpdateView(self, view:discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view

    @commands.command(description = "Use this command to get information about all available commands.",
                    brief = "Sends this help page!",
                    usage = "help [page or command]:\nExample:`help 1`, `help invite`")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def help(self, ctx:commands.Context, HelpInput):
        # sourcery skip: de-morgan, useless-else-on-loop
        # 3 types of commands, Chat, Slash (/) And all.
        # all_list = self.bot.all_commands # Command raised an exception: AttributeError: 'str' object has no attribute 'name'
        # slash_list = self.bot.application_commands # Command raised an exception: AttributeError: 'str' object has no attribute 'name'
        chat_list = self.bot.commands
        view = View()
        if HelpInput is None:
            HelpInput = 1
        try:
            HelpInput = int(HelpInput)
            if HelpInput <= 0:
                await ctx.send("The page number cannot be 0 or less then 0.")
                return
        except Exception as e:
            logging.error(f"Help.py: {e}")

        if isinstance(HelpInput, int):
            ButtonLeft = await self.CreateButton(label=f"Help {HelpInput-1}", style=discord.ButtonStyle.primary)
            ButtonRight = await self.CreateButton(label=f"Help {HelpInput+1}", style=discord.ButtonStyle.primary)

            async def ButtonAction(interaction: discord.Interaction, HelpInput):
                embed = await self.CreateHelpEmbed(HelpInput=HelpInput, chat_list=chat_list)
                ButtonLeft.label = f"Help {HelpInput-1}"
                ButtonRight.label = f"Help {HelpInput+1}"
                MoreThenMax = (HelpInput * config.help.max_per_page) >= len(chat_list)
                if not HelpInput <= 1 and not MoreThenMax:
                    NewView = await self.UpdateView(view, ButtonLeft, ButtonRight)
                elif HelpInput <= 1:
                    NewView = await self.UpdateView(view, ButtonRight)
                elif MoreThenMax:
                    NewView = await self.UpdateView(view, ButtonLeft)
                await interaction.response.edit_message(embed=embed, view=NewView)

            async def ButtonLeftAction(interaction: discord.Interaction):
                nonlocal HelpInput
                HelpInput -= 1
                await ButtonAction(interaction, HelpInput)

            async def ButtonRightAction(interaction: discord.Interaction):
                nonlocal HelpInput
                HelpInput += 1
                await ButtonAction(interaction, HelpInput)

            ButtonLeft.callback = ButtonLeftAction
            ButtonRight.callback = ButtonRightAction
            view.add_item(ButtonLeft)
            view.add_item(ButtonRight)
            if HelpInput <= 1:
                view.remove_item(ButtonLeft)
        embed = await self.CreateHelpEmbed(HelpInput=HelpInput, chat_list=chat_list)
        await ctx.send(embed=embed, view=view)

async def setup(bot:commands.Bot):
    await bot.add_cog(Help(bot))