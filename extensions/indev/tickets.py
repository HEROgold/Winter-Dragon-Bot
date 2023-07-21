import datetime
import logging
from typing import Optional

import discord
import discord.ui
from discord import app_commands
from discord.ext import commands, tasks

import config
from tools import app_command_tools
from tools.database_tables import engine, Session
from tools.database_tables import Channel
from tools.database_tables import Tickets as DbTickets

date_format = "%m/%d/%Y at %H:%M:%S"
DB_CHANNEL_TYPE = "tickets"
# TODO:
# rewrite own
# use dropdown menus


class TicketView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180, channel: discord.abc.GuildChannel) -> None:
        super().__init__(timeout=timeout)
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.cooldown = commands.CooldownMapping.from_cooldown(1, config.Tickets.MAX_COOLDOWN, commands.BucketType.member)
        self.channel: discord.TextChannel = channel


    @discord.ui.button(label="Close Current Ticket", style=discord.ButtonStyle.green, custom_id="ticket_view:close_existing_ticket")
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
        support_role: Optional[discord.Role] = None,
    ) -> None:
        self.logger.debug(f"{interaction.user} closed a ticket")

        channel_name = f"{interaction.user.name}'s ticket"
        with Session(engine) as session:
            ticket_channel = session.query(Channel).where(
                Channel.name == channel_name,
                Channel.type == DB_CHANNEL_TYPE
            ).first()

        dc_thread = discord.utils.get(interaction.guild.threads, id=ticket_channel.id)
        await dc_thread.edit(locked=True)


    @discord.ui.button(label="Create A Ticket", style=discord.ButtonStyle.green, custom_id="ticket_view:create_new_ticket")
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
        support_role: Optional[discord.Role] = None,
    ) -> None:
        "https://discordpy.readthedocs.io/en/stable/api.html?highlight=thread#discord.Thread"
        # TODO: Create a thread in self.channel, add button presser, and add support role
        self.logger.debug(f"{interaction.user} created a ticket")

        if retry := self.cooldown.get_bucket(interaction.message).update_rate_limit():
            await interaction.response.send_message(f"Slow down! Try again in {round(retry, 1)} seconds!", ephemeral=True)
            return

        channel_name = f"{interaction.user.name}'s ticket"

        with Session(engine) as session:
            ticket_channel = session.query(Channel).where(
                Channel.name == channel_name,
                Channel.type == DB_CHANNEL_TYPE
            ).first()

            # TODO: test `is` or `==`
            ticket = session.query(DbTickets).where(
                DbTickets.closed == False,
                DbTickets.channel == ticket_channel
            ).first()

            self.logger.debug(f"{ticket_channel=} IS part of {ticket=}")

        if ticket_channel is not None:
            dc_thread_channel = discord.utils.get(interaction.guild.threads, id=ticket_channel.id)
            await interaction.response.send_message(f"You already have a ticket opened at {dc_thread_channel.mention}", ephemeral=True)
            return

        thread_channel = await self.channel.create_thread(
            name = channel_name,
            auto_archive_duration = 10080, # 10080 7 days in minutes
            reason = f"Ticket opened by {interaction.user.name}",
        )

        await thread_channel.add_user(interaction.user)

        for member in support_role.members:
            await thread_channel.add_user(member)

        # overwrites = {
        #     interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        #     interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
        #     interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
        #     support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True, embed_links=True),
        # }

        self.logger.debug(f"Creating ticket thread for {interaction.user} at {thread_channel=}")

        # Message that gets send when new ticket channel is made.
        await thread_channel.send(f"{interaction.user.mention} Hello!\n a {support_role.mention} will be with you soon.")
        await interaction.response.send_message(f"Opened a ticket at {thread_channel.mention}", ephemeral=True)


# TODO: Add dynamic cooldown between adding/removing ticket channels
# TODO: Add Similar TODO for autochannel, logChannels etc

class Tickets(commands.GroupCog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.act = app_command_tools.Converter(bot=bot)
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")


    async def cog_load(self) -> None:
        self.database_cleanup.start()


    @tasks.loop(seconds=3600)
    async def database_cleanup(self) -> None:
        self.logger.info("cleaning tickets")
        with Session(engine) as session:
            seven_days_from_today = datetime.datetime.now() - datetime.timedelta(days=7)
            tickets = session.query(DbTickets).where(
                DbTickets.closed == False,
                DbTickets.start_datetime <= seven_days_from_today
            ).all()

            closed_start = "~CLOSED"

            for ticket in tickets:
                self.logger.debug(f"cleaning {ticket=}")
                ticket.closed = True
                channel: discord.Thread = self.bot.get_channel(id=ticket.channel.id)
                if closed_start not in channel.name:
                    self.logger.debug(f"closing {ticket=}")
                    closed_name = "~CLOSED TIMEOUT~"
                    await channel.edit(name=f"{channel.name} {closed_name}")
                                            # await channel.delete(reason="Ticket cleanup")
            session.commit()

    @database_cleanup.before_loop
    async def before_update(self) -> None:
        self.logger.info("Waiting until bot is online")
        await self.bot.wait_until_ready()


    @app_commands.checks.has_permissions(manage_channels = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    @app_commands.command(name="create", description="Create a ticket channel and allow users to create new tickets")
    async def slash_ticket_create(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            channel = session.query(Channel).where(
                Channel.type == DB_CHANNEL_TYPE,
                Channel.guild_id == interaction.guild.id
            ).first()
            _, c_mention = await self.act.get_app_sub_command(self.slash_ticket_remove)

            if channel:
                await interaction.response.send_message(f"Ticket channel already set up, use {c_mention} to remove and disable it.", ephemeral=True)
                return

            dc_channel = await interaction.guild.create_text_channel(name="Tickets", reason="Removing Tickets channel")
            session.add(Channel(
                id = dc_channel.id,
                name = f"{dc_channel.name}",
                type = DB_CHANNEL_TYPE,
                guild_id = interaction.guild.id,
            ))
            session.commit()

            await dc_channel.send(view=TicketView(channel=dc_channel, timeout=None))
            await interaction.response.send_message(f"Ticket channel is set up, use {c_mention} to remove and disable it.", ephemeral=True)


    @app_commands.checks.has_permissions(manage_channels = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    @app_commands.command(name="remove", description="Remove a ticket channel and current tickets")
    async def slash_ticket_remove(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            channel = session.query(Channel).where(
                Channel.type == DB_CHANNEL_TYPE,
                Channel.guild_id == interaction.guild.id
            ).first()

            if not channel:
                await interaction.response.send_message("Ticket channel not found", ephemeral=True)
                return

            dc_channel: discord.TextChannel = self.bot.get_channel(id=channel.id)
            await dc_channel.delete()

            session.delete(channel)
            session.commit()
        await interaction.response.send_message("Ticket channel removed", ephemeral=True)


# class TO_REMOVE:

#     class TicketView(discord.ui.View):
#     def __init__(self) -> None:
#         super().__init__(timeout=None)
#         self.cooldown = commands.CooldownMapping.from_cooldown(1, 300, commands.BucketType.member)


#     # FIXME: Pressing create ticket button, doesn't create ticket.
#     @discord.ui.button(
#         label="Create A Ticket", style=discord.ButtonStyle.green, custom_id="Ticket Bot"
#     )
#     async def ticket(
#         self,
#         interaction: discord.Interaction,
#         button: discord.ui.Button,
#         support_role: typing.Optional[discord.Role] = None,
#         category_channel: typing.Optional[discord.CategoryChannel] = None,
#     ) -> None:
#         self.logger.debug(f"{interaction.user} pressed a `Create Ticket` button")
#         if retry := self.cooldown.get_bucket(interaction.message).update_rate_limit():
#             await interaction.response.send_message(f"Slow down! Try again in {round(retry, 1)} seconds!", ephemeral=True)
#             return
#         if category_channel:
#             ticket_channel = utils.get(category_channel, name=f"{interaction.user.id}-ticket")
#         else:
#             ticket_channel = utils.get(interaction.guild.text_channels, name=f"{interaction.user.id}-ticket")
#         if ticket_channel is not None:
#             await interaction.response.send_message(f"You already have a ticket opened at {ticket_channel.mention}", ephemeral=True)
#             return
#         overwrites = {
#             interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
#             interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
#             interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
#             support_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True, embed_links=True),
#         }
#         self.logger.debug(f"Creating ticket for {interaction.user}")
#         channel = await category_channel.create_text_channel(
#             name=f"{interaction.user.id}-ticket",
#             overwrites=overwrites,
#             reason=f"Ticket opened by {interaction.user.name}",
#             )
#         # Message that gets send when new ticket channel is made.
#         await channel.send(f"{interaction.user.mention} Hello!\n a {support_role.mention} will be with you soon.", view=MainView())
#         await interaction.response.send_message(f"Opened a ticket at {channel.mention}", ephemeral=True)


#     class ConfirmClose(discord.ui.View):
#     def __init__(self) -> None:
#         super().__init__(timeout=None)


#     @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red, custom_id="Confirm")
#     async def confirm_button(interaction: discord.Interaction, button: discord.Button) -> None: # NOSONAR
#         channel = utils.get(interaction.guild.text_channels, name=f"{interaction.user.id}-ticket")
#         overwrite = channel.overwrites_for(interaction.user)
#         overwrite.update(view_channel=False)
#         await channel.set_permissions(interaction.user, overwrite=overwrite)
#         closed_embed = discord.Embed(
#             title="Ticket closed!",
#             description=f"This ticket has been closed by: {interaction.user.mention}",
#             color= random.choice(RAINBOW))
#         support_embed = discord.Embed(
#             title="Support Team Controls",
#             description="The below buttons is for the **Support Team** or **Admin.**",
#             color= random.choice(RAINBOW))

#         await interaction.response.send_message(embeds=[closed_embed, support_embed], view=Transcript())


#     class MainView(discord.ui.View):
#     def __init__(self) -> None:
#         super().__init__(timeout=None)


#     @discord.ui.button(label="Close ticket!", style=discord.ButtonStyle.red, custom_id="Close")
#     async def close(interaction: discord.Interaction, button: discord.Button) -> None: # NOSONAR
#         embed = discord.Embed(title="Are you sure that you wanna close this ticket?", color=discord.Color.red())
#         await interaction.response.send_message(embed=embed, view=ConfirmClose(), ephemeral=True)



#     class Transcript(discord.ui.View):
#     TICKETS_DIRECTORY = "./database/Tickets"

#     def __init__(self) -> None:
#         super().__init__(timeout=None)



#     @discord.ui.button(label="Transcript!", style=discord.ButtonStyle.blurple, custom_id="Close")
#     async def transcript(interaction: discord.Interaction, button: discord.Button) -> None: # NOSONAR
#         await interaction.response.defer()
#         if os.path.exists(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.id}.md"):
#             await interaction.followup.send(
#                 "A transcript is already being generated", ephemeral=True
#             )
#             return
#         with open(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.id}.md", "a") as f:
#             f.write(f"Transcript of {interaction.channel.name}:\n\n")
#             async for message in interaction.channel.history(limit=None, oldest_first=True):
#                 created = datetime.strftime(message.created_at, date_format)
#             if message.edited_at:
#                 edited = datetime.strftime(message.edited_at, date_format)
#                 f.write(
#                     f"{message.author} on {created}: {message.clean_content} (Edited at {edited})\n"
#                 )
#             else:
#                 f.write(f"{message.author} on {created}: {message.clean_content}\n")
#             generated_time = datetime.now().strftime(date_format)
#             f.write(f"Generated at {generated_time}\nDate Formatting: MM/DD/YY\nTimezone: UTC")
#         with open(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.id}.md", "rb") as f:
#             await interaction.followup.send(file=discord.File(f, f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.name}.md"))
#         os.remove(f"{Transcript.TICKETS_DIRECTORY}/{interaction.channel.name}.md")



#     class Tickets(commands.GroupCog):
#     NOT_TICKET_MSG = "This isn't a ticket!"
#     logger: logging.Logger = None
#     data = None

#     def __init__(self, bot) -> None:
#         self.bot = bot
#         self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
#         self.act = app_command_tools.Converter(bot=self.bot)


#     @app_commands.command(name="start", description="Launches ticket system.")
#     @app_commands.describe(support="The Role who would be mentioned on support.")
#     @app_commands.default_permissions(manage_guild=True)
#     @app_commands.checks.cooldown(3, 60, key=lambda i: i.guild_id)
#     @app_commands.checks.bot_has_permissions(manage_channels=True)
#     async def slash_start(
#         self,
#         interaction: discord.Interaction,
#         support: discord.Role,
#         category_channel: discord.CategoryChannel,
#     ) -> None:
#         embed = discord.Embed(title="Ticket", description="Click the below button to open a ticket!")
#         await interaction.channel.send(embed=embed, view=TicketView())
#         await interaction.response.send_message("Ticketing System Started.", ephemeral=True)


#     @app_commands.command(name="close", description="Closes the ticket")
#     async def close(self, interaction: discord.Interaction) -> None:
#         if "-ticket" in interaction.channel.name:
#             embed = discord.Embed(
#                 title="Are you sure that you wanna close this ticket?", color=discord.Color.red())
#             await interaction.response.send_message(embed=embed, view=ConfirmClose(), ephemeral=True)
#         else:
#             await interaction.response.send_message(self.NOT_TICKET_MSG)


#     @app_commands.command(name="add", description="Add members to the ticket")
#     @app_commands.describe(user="The user who you want to add to the ticket")
#     @app_commands.default_permissions(manage_guild=True)
#     async def slash_add(self, interaction: discord.Interaction, user: discord.Member) -> None:
#         if "-ticket" in interaction.channel.name:
#             await interaction.channel.set_permissions(user, view_channel=True, send_messages=True, attach_files=True, embed_links=True)
#             await interaction.response.send_message(f"{user.mention} has been added to ticket by {interaction.user.mention}",ephemeral=True,)
#         else:
#             await interaction.response.send_message(self.NOT_TICKET_MSG)


#     @app_commands.command(name="remove", description="Removes members from the ticket")
#     @app_commands.describe(user="The user who you want to remove from the ticket")
#     @app_commands.default_permissions(manage_guild=True)
#     async def slash_remove(self, interaction: discord.Interaction, user: discord.Member) -> None:
#         if "-ticket" in interaction.channel.name:
#             await interaction.channel.set_permissions(user, overwrite=None)
#             await interaction.response.send_message(f"{user.mention} has been removed from ticket by {interaction.user.mention}",ephemeral=True,)
#         else:
#             await interaction.response.send_message(self.NOT_TICKET_MSG)


#     @app_commands.command(name="transcript", description="Generates a transcript of the ticket")
#     @app_commands.default_permissions(manage_guild=True)
#     async def transcript(self, interaction: discord.Interaction) -> None:
#         if "-ticket" not in interaction.channel.name:
#             await interaction.response.send_message(self.NOT_TICKET_MSG)
#             return
#         await interaction.response.defer()
#         if os.path.exists(f"{self.Ticketsdatabase}{interaction.channel.id}.md"):
#             await interaction.followup.send(
#                 "A transcript is already being generated", ephemeral=True
#             )
#             return
#         with open(f"{self.Ticketsdatabase}{interaction.channel.id}.md", "a") as f:
#             f.write(f"Transcript of {interaction.channel.name}:\n\n")
#         async for message in interaction.channel.history(limit=None, oldest_first=True):
#             created = datetime.strftime(message.created_at, date_format)
#             if message.edited_at:
#                 edited = datetime.strftime(message.edited_at, date_format)
#                 f.write(
#                     f"{message.author} on {created}: {message.clean_content} (Edited at {edited})\n"
#                 )
#             else:
#                 f.write(f"{message.author} on {created}: {message.clean_content}\n")
#         generated_time = datetime.now().strftime(date_format)
#         f.write(f"Generated at {generated_time}\nDate Formatting: MM/DD/YY\nTimezone: UTC")
#         with open(f"{self.Ticketsdatabase}{interaction.channel.id}.md", "rb") as f:
#             await interaction.followup.send(file=discord.File(f, f"{self.Ticketsdatabase}{interaction.channel.name}.md"))
#         os.remove(f"{self.Ticketsdatabase}{interaction.channel.name}.md")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
