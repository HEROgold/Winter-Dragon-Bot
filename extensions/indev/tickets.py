import datetime
import itertools
import logging
import random

import discord
import discord.ui
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy.orm import joinedload

from _types.bot import WinterDragon
from _types.cogs import GroupCog
from _types.enums import ChannelTypes
from tools.config import config
from tools.database_tables import Channel, Session, Ticket, Transaction, User, engine


c_type = ChannelTypes.TICKETS.name
CLOSED_USER = "~CLOSED USER~"
CLOSED_TIMEOUT = "~CLOSED TIMEOUT~"

# TODO: rewrite own, use dropdown menus
# Database tables already rewritten.
# Test current state


class TicketView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180, channel: discord.TextChannel) -> None:
        super().__init__(timeout=timeout)
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.cooldown = commands.CooldownMapping.from_cooldown(1, config.getint("Tickets", "MAX_COOLDOWN"), commands.BucketType.member)
        self.channel = channel


    @discord.ui.button(label="Close Current Ticket", style=discord.ButtonStyle.green, custom_id="ticket_view:close_existing_ticket")
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,  # noqa: ARG002
        support_role: discord.Role | None = None,  # noqa: ARG002
    ) -> None:
        self.logger.info(f"{interaction.user} closed a ticket")

        with Session(engine) as session:
            ticket = session.query(Ticket).where(
                Ticket.user_id == interaction.user.id,
                Ticket.channel_id == interaction.channel.id,
            ).first()
            ticket.close()

        channel = discord.utils.get(interaction.channel.threads, id=ticket.channel.id)
        await channel.edit(
            name=f"{channel.name} {CLOSED_USER}",
            locked=True,
            reason=f"Locked by user {interaction.user.mention}",
        )


    @discord.ui.button(label="Create A Ticket", style=discord.ButtonStyle.green, custom_id="ticket_view:create_new_ticket")
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,  # noqa: ARG002
        support_role: discord.Role | None = None,
    ) -> None:
        "https://discordpy.readthedocs.io/en/stable/api.html?highlight=thread#discord.Thread"
        # TODO: Create a thread in self.channel, add button presser, and add support role
        self.logger.info(f"{interaction.user} created a ticket")

        if retry := self.cooldown.get_bucket(interaction.message).update_rate_limit(): # type: ignore
            await interaction.response.send_message(f"Slow down! Try again in {round(retry, 1)} seconds!", ephemeral=True)
            return

        channel_name = f"{interaction.user.name}'s ticket"

        with Session(engine) as session:
            if (
                ticket := session.query(Ticket).where(
                    Ticket.user_id == interaction.user.id,
                    # Ticket.channel_id == interaction.channel.id,
                    Ticket.is_closed == False, # noqa: E712
                ).first()
            ):
                dc_channel = discord.utils.get(self.channel.threads, id=ticket.channel.id)
                await interaction.response.send_message(f"You already have a ticket opened at {dc_channel.mention}", ephemeral=True)
                return

        thread_channel = await self.channel.create_thread(
            name = channel_name,
            auto_archive_duration = 10080, # 10080 = 7 days in minutes
            reason = f"Ticket opened by {interaction.user.name}",
        )

        with Session(engine) as session:
            session.add(Ticket(
                id=None,
                title=f"Ticket for user {interaction.user.id} in channel {thread_channel.id}",
                description=f"Description for ticket for user {interaction.user.id} in channel {thread_channel.id}",
                opened_at=datetime.datetime.now(),  # noqa: DTZ005
                is_closed=False,
                user_id=interaction.user.id,
                channel_id=thread_channel.id,
            ))

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
        await interaction.response.send_message(f"Opened a ticket at {thread_channel.mention}", ephemeral=True, delete_after=10)


# TODO: Add dynamic cooldown between adding/removing ticket channels
# TODO: Add Similar TODO for autochannel, logChannels etc

class Tickets(GroupCog):
    async def cog_load(self) -> None:
        self.database_cleanup.start()


    @tasks.loop(seconds=3600)
    async def database_cleanup(self) -> None:
        self.logger.info("cleaning tickets")
        with Session(engine) as session:
            seven_days_before_today = datetime.datetime.now() - datetime.timedelta(days=7)  # noqa: DTZ005
            tickets = session.query(Ticket).where(
                Ticket.is_closed == False, # noqa: E712
                Ticket.opened_at <= seven_days_before_today,
            ).options(joinedload(Ticket.transactions)).all()

            for ticket in tickets:
                if not ticket.closed_at:
                    continue

                # TODO: find out if sorted returns oldest or newest.
                latest_transactions: list[Transaction] = sorted(
                    ticket.transactions,
                    key=lambda x: x.timestamp,
                )
                if latest_transactions[0].timestamp <= seven_days_before_today:
                    # if latest response is less then 7 days ago, skip it
                    continue

                self.logger.info(f"closing {ticket=}")
                ticket.close()
                channel = self.bot.get_channel(ticket.channel.id)
                await channel.edit(name=f"{channel.name} {CLOSED_TIMEOUT}")

                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = False
                overwrite.read_messages = True

                found_users = self.bot.get_all_members()

                for user in [*ticket.helpers, ticket.user]:
                    await channel.set_permissions(
                        target=discord.utils.get(found_users, user.id),
                        overwrite=overwrite,
                        reason="Ticket cleanup",
                    )
                # await channel.delete(reason="Ticket cleanup")
            session.commit()


    @database_cleanup.before_loop
    async def before_update(self) -> None:
        await self.bot.wait_until_ready()


    @app_commands.checks.has_permissions(manage_channels = True)
    @app_commands.checks.bot_has_permissions(manage_channels = True)
    @app_commands.command(name="create", description="Create a ticket channel and allow users to create new tickets")
    async def slash_ticket_create(self, interaction: discord.Interaction) -> None:
        with Session(engine) as session:
            channel = session.query(Channel).where(
                Channel.type == c_type,
                Channel.guild_id == interaction.guild.id,
            ).first()
            c_mention = await self.get_command_mention(self.slash_ticket_remove)

            if channel:
                await interaction.response.send_message(f"Ticket channel already set up, use {c_mention} to remove and disable it.", ephemeral=True)
                return

            dc_channel = await interaction.guild.create_text_channel(name="Tickets", reason="Removing Tickets channel")
            Channel.update(Channel(
                id = dc_channel.id,
                name = f"{dc_channel.name}",
                type = c_type,
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
            if (
                channel := session.query(Channel).where(
                    Channel.type == c_type,
                    Channel.guild_id == interaction.guild.id,
                ).first()
            ):
                dc_channel: discord.TextChannel = self.bot.get_channel(id=channel.id)
                await dc_channel.delete()
                session.delete(channel)
                session.commit()
                await interaction.response.send_message("Ticket channel removed", ephemeral=True)
                return

        await interaction.response.send_message("Ticket channel not found", ephemeral=True)
        return


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Tickets(bot))


def insert_data() -> None:  # sourcery skip: identity-comprehension
    COUNT = 48

    # Create multiple instances of users
    users = [User(id=i) for i in range(1, (COUNT // 2 - 1))]
    print(f"{users=}")

    # Create multiple instances of channels
    channels = [
        Channel(id=i, name=f"Channel {i}") for i in range((COUNT // 2), COUNT)
    ]
    print(f"{channels=}")

    # Create multiple instances of tickets
    tickets: list[Ticket] = []
    allowed = list(range(COUNT, COUNT**2))
    for user, channel in itertools.product(users, channels):
        open_time = datetime.now()
        if random.choice([False, True]):
            ticket = Ticket(
                id=allowed.pop(0),
                title=f"Ticket for user {user.id} in channel {channel.id}",
                description=f"Description for ticket for user {user.id} in channel {channel.id}",
                opened_at=open_time,
                is_closed=False,
                user_id=user.id,
                channel_id=channel.id,
            )
        else:
            ticket = Ticket(
                id=allowed.pop(0),
                title=f"Ticket for user {user.id} in channel {channel.id}",
                description=f"Description for ticket for user {user.id} in channel {channel.id}",
                opened_at=open_time,
                is_closed=True,
                closed_at=datetime.now(),
                user_id=user.id,
                channel_id=channel.id,
            )
        tickets.append(ticket)
    print(f"{tickets=}")

    # Create multiple instances of transactions
    transactions: list[Transaction] = []
    for ticket, user in itertools.product(tickets, users):
        transaction = Transaction(
            timestamp=datetime.now(),
            action=f"Action for ticket {ticket.id} by user {user.id}",
            details=f"Details for transaction for ticket {ticket.id} by user {user.id}",
            ticket_id=ticket.id,
            responder_id=user.id,
        )
        transactions.append(transaction)
    print(f"{transactions=}")

    # Insert test data into the database
    with Session(engine) as session:
        session.add_all(users + channels + tickets + transactions)
        session.commit()


def tables_test() -> None:
    with Session(engine) as session:
        # Query tickets and their related data
        # is joinedload necessary?
        tickets = session.query(Ticket).options(
            joinedload(Ticket.user),
            joinedload(Ticket.channel),
            joinedload(Ticket.transactions),
            joinedload(Ticket.helpers),
        ).all()

    # Print ticket data and related data
    for ticket in tickets:
        print(f"Ticket ID: {ticket.id}")
        print(f"Title: {ticket.title}")
        print(f"Description: {ticket.description}")
        print(f"User ID: {ticket.user.id}")
        print(f"Channel ID: {ticket.channel.id}")
        print("Transaction IDs:", [transaction.id for transaction in ticket.transactions])
        print("Helper IDs:", [helper.id for helper in ticket.helpers])


def main() -> None:
    insert_data()
    tables_test()
    # random_query()


if __name__ == "__main__":
    main()
