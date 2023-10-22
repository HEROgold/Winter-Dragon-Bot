import datetime
import logging
import random
from textwrap import dedent

import discord
import num2words
from discord import app_commands
from discord.ext import tasks
from discord.interactions import Interaction

import tools.rainbow as rainbow
from tools.config_reader import config
from tools.database_tables import AssociationUserPoll as AUP
from tools.database_tables import Channel
from tools.database_tables import Poll as PollDb
from tools.database_tables import Session, engine
from _types.cogs import GroupCog
from _types.bot import WinterDragon
from _types.modal import Modal

POLL_TYPE = "poll"


# FIXME: Doesn't post in set channel
class PollModal(Modal):
    place_holder = "Empty Answer"
    q1 = discord.ui.TextInput(label="Answer #1", placeholder=place_holder, required=True)
    q2 = discord.ui.TextInput(label="Answer #2", placeholder=place_holder, required=True)
    q3 = discord.ui.TextInput(label="Answer #3", placeholder=place_holder, required=False)
    q4 = discord.ui.TextInput(label="Answer #4", placeholder=place_holder, required=False)
    q5 = discord.ui.TextInput(label="Answer #5", placeholder=place_holder, required=False)


    def __init__(self, end_epoch: datetime.datetime, content: str, poll_channel: discord.TextChannel) -> None:
        self.end_epoch = end_epoch
        self.content = content
        self.poll_channel = poll_channel
        super().__init__(title=f"{content}", timeout=180)


    async def on_submit(self, interaction: Interaction) -> None:
        answers = (
            self.q1,
            self.q2,
            self.q3,
            self.q4,
            self.q5,
        )
        if len(answers) < 2:
            await interaction.response.send_message(
                "Please add at least 2 answers",
                ephemeral=True
            )
            return

        emb = discord.Embed(title="Poll", description=f"{self.title}\n\n", color=random.choice(rainbow.RAINBOW))
        emb.timestamp = datetime.datetime.now()
        emb.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
        emb.set_footer(text="You may only vote once, and cannot change.")

        # # create dynamic emoji from 1 to 5 > change name for 10 to :keycap_ten:
        for i, answer in enumerate(answers):
            emb.add_field(name=f":{num2words.num2words(i+1)}:", value=answer.value, inline=True)

        # # Add epoch relative time left after adding options. Discord <t:0000:R> doesn't work on footer.
        emb.add_field(name="Time Left", value=f"<t:{self.end_epoch}:R>", inline=False)

        msg = await self.poll_channel.send(embed=emb)
        await interaction.response.send_message(f"Poll created at {msg.jump_url}", ephemeral=True, delete_after=10)

        ALLOWED_EMOJIS = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
        for i, answer in enumerate(answers):
            if answer is None:
                continue
            await msg.add_reaction(ALLOWED_EMOJIS[i])

        with Session(engine) as session:
            session.add(PollDb(
                channel_id = interaction.channel.id,
                message_id = interaction.message.id,
                content = self.content,
                end_date = self.end_epoch,
            ))
            session.commit()


class Poll(GroupCog):
    @staticmethod
    def get_polls() -> list[PollDb]:
        with Session(engine) as session:
            return session.query(PollDb).all()


    @staticmethod
    def add_vote_to_poll(poll_id: int, user_id: int, vote_option: int) -> None:
        with Session(engine) as session:
            session.add(AUP(
                poll_id = poll_id,
                user_id = user_id,
                voted_value = vote_option,
            ))
            session.commit()


    @staticmethod
    def get_finished_polls() -> list[PollDb]:
        with Session(engine) as session:
            return session.query(PollDb).where(PollDb.end_date >= datetime.datetime.now).all()


    @staticmethod
    def get_seconds(
        seconds : int = 0, minutes: int = 0, hours: int = 0, days: int = 0
    ) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds


    @classmethod
    def get_future_epoch(
        cls, minutes: int=0, hours: int=0, days: int=0
    ) -> int:
        return int((
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=cls.get_seconds(minutes=minutes, hours=hours, days=days)
            )).timestamp())


    @tasks.loop(seconds=60)
    async def announce_winners(self) -> None:
        with Session(engine) as session:
            finished = session.query(PollDb).where(
                PollDb.end_date >= datetime.datetime.now(),
                PollDb.channel_id,
            )
            for i in finished:
                votes = [i.voted_value for i in session.query(AUP).where(AUP.poll_id == i.id).all()]
                # https://discord.com/channels/336642139381301249/1147999910910758983
                vote_result = "\n"
                for i in [5, 4, 3, 2, 1]:
                    if votes.count(i) == 0:
                        continue
                    vote_result += f":{num2words.num2words(i)}:: {votes.count(i)}\n"

                message_url = f"https://discord.com/channels/{i.channel_id}/{i.message_id}"
                self.bot.get_channel(i.channel_id).send(f"Poll {message_url} finished with results: {vote_result}")


    poll_channel = app_commands.Group(name="channel", description="Manage poll channels")

    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @poll_channel.command(name="set", description="Set the poll channel")
    async def slash_set_poll_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        with Session(engine) as session:
            if (
                found := session.query(Channel).where(
                    Channel.type == POLL_TYPE,
                    Channel.guild_id == channel.guild.id
                ).first()
            ):
                found.id = channel.id
                found.name = channel.name
                session.commit()
                await interaction.response.send_message(dedent(f"""
                    Channel set to {self.bot.get_channel(found.id).mention}
                """))
                return

            Channel.update(Channel(
                id = channel.id,
                name = channel.name,
                type = POLL_TYPE,
                guild_id = channel.guild.id,
            ))
            session.commit()


    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @poll_channel.command(name="remove", description="Remove the poll channel")
    async def slash_remove_poll_channel(self, interaction: discord.Interaction):
        with Session(engine) as session:
            if (
                found := session.query(Channel).where(
                    Channel.type == POLL_TYPE,
                    Channel.guild_id == interaction.guild.id
                ).first()
            ):
                _, remove_channel_command = self.act.get_app_sub_command(self.slash_remove_poll_channel)

                self.bot.get_channel(found.id).delete(
                    reason=f"Removed by {interaction.user.mention} because of {remove_channel_command}"
                )
                session.delete(found)

                await interaction.response.send_message(f"Removed channel, you can add one again by using {add_channel_command}")
                session.commit()
                return

            _, add_channel_command = self.act.get_app_sub_command(self.slash_set_poll_channel)
            await interaction.response.send_message(f"Channel not found, Please add by using {add_channel_command}")


    @app_commands.command(name="create", description="Create a poll")
    async def slash_poll_create( 
        self,
        interaction: discord.Interaction,
        question: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
    ) -> None:
        if sum((minutes, hours, days)) == 0:
            await interaction.response.send_message("No duration time given", ephemeral=True)
            return

        with Session(engine) as session:
            if channel := session.query(Channel).where(
                Channel.type == POLL_TYPE,
                Channel.guild_id == interaction.guild.id
            ).first():
                self.logger.debug(f"{channel=}")
                await interaction.response.send_modal(PollModal(
                    end_epoch = self.get_future_epoch(minutes, hours, days),
                    content = question,
                    poll_channel = channel
                ))
                return
            else:
                self.logger.warning(f"No poll channel found to send poll to for {interaction.guild=}")

            # FIXME: error on self.act.get_app_sub_command: type(error)=<class 'discord.app_commands.errors.CommandInvokeError'>, error.args=("Command 'create' raised an exception: AttributeError: 'NoneType' object has no attribute 'name'",)
            # Weird interaction with app_commands.Group()
            self.logger.debug(f"Getting {self.slash_set_poll_channel}")
            _, custom_mention = await self.act.get_app_sub_command(self.slash_set_poll_channel)

            if interaction.user.guild_permissions.manage_channels:
                await interaction.response.send_message(
                    f"No channel found to send poll. use {custom_mention} to set one",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "No channel found to send poll.",
                    ephemeral=True
                )


async def setup(bot: WinterDragon) -> None:
	await bot.add_cog(Poll(bot))