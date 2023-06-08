import datetime
import logging
import os
import random
import typing
from datetime import datetime

import discord
import discord.ui
from discord import app_commands, utils
from discord.ext import commands

import config
from rainbow import RAINBOW
from tools import app_command_tools
from tools.database_tables import engine, Session

date_format = "%m/%d/%Y at %H:%M:%S"

# TODO:
# rewrite own


class TicketView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 300, commands.BucketType.member)


    # FIXME: Pressing create ticket button, doesn't create ticket.
    @discord.ui.button(
        label="Create A Ticket", style=discord.ButtonStyle.green, custom_id="Ticket Bot"
    )
    async def ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
        support_role: typing.Optional[discord.Role] = None,
        category_channel: typing.Optional[discord.CategoryChannel] = None,
    ) -> None:
        Tickets.logger.debug(f"{interaction.user} pressed a `Create Ticket` button")
        if retry := self.cooldown.get_bucket(interaction.message).update_rate_limit():
            await interaction.response.send_message(f"Slow down! Try again in {round(retry, 1)} seconds!", ephemeral=True)
            return
        if category_channel:
            ticket_channel = utils.get(category_channel, name=f"{interaction.user.id}-ticket")
        else:
            ticket_channel = utils.get(interaction.guild.text_channels, name=f"{interaction.user.id}-ticket")
        if ticket_channel is not None:
            await interaction.response.send_message(f"You already have a ticket opened at {ticket_channel.mention}", ephemeral=True)
            return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True, embed_links=True),
        }
        Tickets.logger.debug(f"Creating ticket for {interaction.user}")
        channel = await category_channel.create_text_channel(
            name=f"{interaction.user.id}-ticket",
            overwrites=overwrites,
            reason=f"Ticket opened by {interaction.user.name}",
            )
        # Message that gets send when new ticket channel is made.
        await channel.send(f"{interaction.user.mention} Hello!\n a {support_role.mention} will be with you soon.", view=MainView())
        await interaction.response.send_message(f"Opened a ticket at {channel.mention}", ephemeral=True)


class ConfirmClose(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red, custom_id="Confirm")
    async def confirm_button(interaction: discord.Interaction, button: discord.Button) -> None: # NOSONAR
        channel = utils.get(interaction.guild.text_channels, name=f"{interaction.user.id}-ticket")
        overwrite = channel.overwrites_for(interaction.user)
        overwrite.update(view_channel=False)
        await channel.set_permissions(interaction.user, overwrite=overwrite)
        closed_embed = discord.Embed(
            title="Ticket closed!",
            description=f"This ticket has been closed by: {interaction.user.mention}",
            color= random.choice(RAINBOW))
        support_embed = discord.Embed(
            title="Support Team Controls",
            description="The below buttons is for the **Support Team** or **Admin.**",
            color= random.choice(RAINBOW))

        await interaction.response.send_message(embeds=[closed_embed, support_embed], view=Transcript())


class MainView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)


    @discord.ui.button(label="Close ticket!", style=discord.ButtonStyle.red, custom_id="Close")
    async def close(interaction: discord.Interaction, button: discord.Button) -> None: # NOSONAR
        embed = discord.Embed(title="Are you sure that you wanna close this ticket?", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, view=ConfirmClose(), ephemeral=True)



class Transcript(discord.ui.View):
    TICKETS_DIRECTORY = "./database/Tickets"

    def __init__(self) -> None:
        super().__init__(timeout=None)



    @discord.ui.button(label="Transcript!", style=discord.ButtonStyle.blurple, custom_id="Close")
    async def transcript(interaction: discord.Interaction, button: discord.Button) -> None: # NOSONAR
        await interaction.response.defer()
        if os.path.exists(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.id}.md"):
            await interaction.followup.send(
                "A transcript is already being generated", ephemeral=True
            )
            return
        with open(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.id}.md", "a") as f:
            f.write(f"Transcript of {interaction.channel.name}:\n\n")
            async for message in interaction.channel.history(limit=None, oldest_first=True):
                created = datetime.strftime(message.created_at, date_format)
            if message.edited_at:
                edited = datetime.strftime(message.edited_at, date_format)
                f.write(
                    f"{message.author} on {created}: {message.clean_content} (Edited at {edited})\n"
                )
            else:
                f.write(f"{message.author} on {created}: {message.clean_content}\n")
            generated_time = datetime.now().strftime(date_format)
            f.write(f"Generated at {generated_time}\nDate Formatting: MM/DD/YY\nTimezone: UTC")
        with open(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.id}.md", "rb") as f:
            await interaction.followup.send(file=discord.File(f, f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.name}.md"))
        os.remove(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.name}.md")



class Tickets(commands.GroupCog):
    NOT_TICKET_MSG = "This isn't a ticket!"
    logger: logging.Logger = None
    data = None

    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.act = app_command_tools.Converter(bot=self.bot)


    @app_commands.command(name="start", description="Launches ticket system.")
    @app_commands.describe(support="The Role who would be mentioned on support.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.cooldown(3, 60, key=lambda i: i.guild_id)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slash_start(
        self,
        interaction: discord.Interaction,
        support: discord.Role,
        category_channel: discord.CategoryChannel,
    ) -> None:
        embed = discord.Embed(title="Ticket", description="Click the below button to open a ticket!")
        await interaction.channel.send(embed=embed, view=TicketView())
        await interaction.response.send_message("Ticketing System Started.", ephemeral=True)


    @app_commands.command(name="close", description="Closes the ticket")
    async def close(self, interaction: discord.Interaction) -> None:
        if "-ticket" in interaction.channel.name:
            embed = discord.Embed(
                title="Are you sure that you wanna close this ticket?", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, view=ConfirmClose(), ephemeral=True)
        else:
            await interaction.response.send_message(self.NOT_TICKET_MSG)


    @app_commands.command(name="add", description="Add members to the ticket")
    @app_commands.describe(user="The user who you want to add to the ticket")
    @app_commands.default_permissions(manage_guild=True)
    async def slash_add(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if "-ticket" in interaction.channel.name:
            await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, attach_files=True, embed_links=True)
            await interaction.response.send_message(f"{user.mention} has been added to ticket by {interaction.user.mention}",ephemeral=True,)
        else:
            await interaction.response.send_message(self.NOT_TICKET_MSG)


    @app_commands.command(name="remove", description="Removes members from the ticket")
    @app_commands.describe(user="The user who you want to remove from the ticket")
    @app_commands.default_permissions(manage_guild=True)
    async def slash_remove(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if "-ticket" in interaction.channel.name:
            await interaction.channel.set_permissions(user, overwrite=None)
            await interaction.response.send_message(f"{user.mention} has been removed from ticket by {interaction.user.mention}",ephemeral=True,)
        else:
            await interaction.response.send_message(self.NOT_TICKET_MSG)


    @app_commands.command(name="transcript", description="Generates a transcript of the ticket")
    @app_commands.default_permissions(manage_guild=True)
    async def transcript(self, interaction: discord.Interaction) -> None:
        if "-ticket" not in interaction.channel.name:
            await interaction.response.send_message(self.NOT_TICKET_MSG)
            return
        await interaction.response.defer()
        if os.path.exists(f"{self.Ticketsdatabase}{interaction.channel.id}.md"):
            await interaction.followup.send(
                "A transcript is already being generated", ephemeral=True
            )
            return
        with open(f"{self.Ticketsdatabase}{interaction.channel.id}.md", "a") as f:
            f.write(f"Transcript of {interaction.channel.name}:\n\n")
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            created = datetime.strftime(message.created_at, date_format)
            if message.edited_at:
                edited = datetime.strftime(message.edited_at, date_format)
                f.write(
                    f"{message.author} on {created}: {message.clean_content} (Edited at {edited})\n"
                )
            else:
                f.write(f"{message.author} on {created}: {message.clean_content}\n")
        generated_time = datetime.now().strftime(date_format)
        f.write(f"Generated at {generated_time}\nDate Formatting: MM/DD/YY\nTimezone: UTC")
        with open(f"{self.Ticketsdatabase}{interaction.channel.id}.md", "rb") as f:
            await interaction.followup.send(file=discord.File(f, f"{self.Ticketsdatabase}{interaction.channel.name}.md"))
        os.remove(f"{self.Ticketsdatabase}{interaction.channel.name}.md")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
