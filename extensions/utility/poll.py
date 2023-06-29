import datetime
import logging
import random

import discord
import num2words
from discord import app_commands
from discord.ext import commands, tasks

import config
import rainbow
from tools import app_command_tools
from tools.database_tables import Poll as PollDb
from tools.database_tables import Session, engine


# TODO: rewrite for sql
class Poll(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member) -> None:
        if user.bot == True:
            return
        with Session(engine) as session:
            poll = session.query(PollDb).where(PollDb.message_id == reaction.message.id).first()

        voted_users: list = poll["Users"]
        vote_epoch_end: int = poll["Time"]
        dm = user.dm_channel or await user.create_dm()
        if user.id not in voted_users and datetime.datetime.now(datetime.timezone.utc).timestamp() <= vote_epoch_end:
            voted_users.append(user.id)
            await reaction.remove(user)
            poll["Votes"][reaction.emoji]["count"] += 1
            self.set_data(self.data)
        elif datetime.datetime.now().timestamp() <= vote_epoch_end:
            await reaction.remove(user)
            await dm.send("You cannot vote anymore, You can only vote for one thing.")
        else:
            await reaction.remove(user)
            await dm.send("You cannot vote anymore, The vote time has ran out.")

    # Rewrite with sql
    @tasks.loop(seconds=60)
    async def anounce_winners(self) -> None:
        for guild_id, guild_data in self.data.items(): #type: ignore
            # self.logger.debug(f"checking {guild_id}")
            # self.logger.debug(f"{guild_data['polls']}")
            for msg_id, poll_data in list(guild_data["polls"].items()):
                # self.logger.debug("looping over polls")
                # self.logger.debug(f"{poll_data}")
                if poll_data["Time"] <= datetime.datetime.now(datetime.timezone.utc).timestamp():
                    # self.logger.debug("Time not met")
                    continue
                # self.logger.debug("Announcing Winner")
                # Get message then edit message with the same embed and add the winning option as text.
                channel = self.bot.get_channel(int(guild_data["poll_channel"])) or await self.bot.fetch_channel(int(guild_data["poll_channel"]))
                msg = channel.get_partial_message(msg_id) or await channel.fetch_message(msg_id)
                self.logger.debug(f"{channel}")
                self.logger.debug(f"{msg}")
                embed = msg.embeds[0]
                self.logger.debug(f"{embed}")
                for field in embed.fields:
                    field.name = "test"
                    field.value = "test"
                    field.inline = False
                    # field.name += f" Votes: {poll_data['polls'][str(msg.id)]['Votes'][field.name[1:-1]]['count']}"
                await msg.edit(embed=embed)
                # del poll_data


    @app_commands.checks.has_permissions()
    @app_commands.command(
        name="create",
        description="Create a poll"
    )
    async def slash_poll_create( 
        self, # NOSONAR
        interaction: discord.Interaction,
        message: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        choice1: str = None,
        choice2: str = None,
        choice3: str = None,
        choice4: str = None,
        choice5: str = None,
        choice6: str = None,
        choice7: str = None,
        choice8: str = None,
        choice9: str = None,
        choice10: str = None,
    ) -> None:
        if sum(minutes, hours, days) == 0:
            await interaction.response.send_message("No time given", ephemeral=True)
            return

        options = [choice1, choice2, choice3, choice4, choice5, choice6, choice7, choice8, choice9, choice10]
        if all(options is None):
            await interaction.response.send_message("No options given for the poll", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        poll_channel_id, poll_channel = await self.get_poll_channels(guild_id)
        
        if not poll_channel_id:
            act = app_command_tools.Converter(bot=self.bot)
            _, custom_mention = await act.get_app_sub_command(self.slash_poll_set_channel)
            await interaction.response.send_message(f"No channel found to send poll. use {custom_mention} to set one", ephemeral=True) # </poll channel:ID>
            return

        emb = discord.Embed(title="Poll", description=f"{message}\n\n", color=random.choice(rainbow.RAINBOW))
        emb.timestamp = datetime.datetime.now()
        emb.set_author(name=interaction.user, icon_url=interaction.user.avatar.url)
        emb.set_footer(text="You may only vote once, and cannot change.")

        # create dynamic emoji from 1 to 10 > change name for 10 to :keycap_ten:
        for i, option in enumerate(options):
            if option is None:
                continue
            j = i+1
            emb.add_field(name=f":{'keycap_ten' if j == 10 else num2words.num2words(j)}:", value=option, inline=True)

        # Add epoch relative time left after adding options. Discord <t:0000:R> doesn't work on footer.
        timeout_epoch = self.get_relative_epoch(minutes, hours, days)
        emb.add_field(name="Time Left", value=f"<t:{timeout_epoch}:R>", inline=False)

        await interaction.response.send_message("Poll created", ephemeral=True, delete_after=10)
        msg = await poll_channel.send(embed=emb)

        ALLOWED_EMOJIS = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟",]
        for i, option in enumerate(options):
            if option is None:
                continue
            await msg.add_reaction(ALLOWED_EMOJIS[i])

        self.data[guild_id]["polls"][str(msg.id)] = {
            "Time": timeout_epoch,
            "Question": message,
            "Votes": {str(ALLOWED_EMOJIS[i]):{"msg":option,"count":0} for i, option in enumerate(options)},
            "Users": [],
        }

        self.set_data(self.data)


    def get_relative_epoch(self, minutes, hours, days) -> int:
        return int(
            (
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                    seconds=self.get_seconds(minutes=minutes, hours=hours, days=days)
                )).timestamp()
        )


    async def get_poll_channels(self, guild_id:str) -> tuple[int, discord.TextChannel]:
        try:
            self.data[guild_id]
        except KeyError:
            self.data[guild_id] = {}
        try:
            poll_channel_id:int = self.data[guild_id]["poll_channel"]
            poll_channel = self.bot.get_channel(poll_channel_id) or await self.bot.fetch_channel(poll_channel_id)
        except (KeyError, discord.errors.NotFound):
            poll_channel_id = None
            poll_channel = None
        try:
            self.data[guild_id]["polls"]
        except KeyError:
            self.data[guild_id]["polls"] = {}
        return poll_channel_id, poll_channel


    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.command(
        name="channel",
        description="Set the poll channel"
    )
    async def slash_poll_set_channel(self, interaction:discord.Interaction, channel:discord.TextChannel) -> None:
        try:
            guild_id = str(interaction.guild.id)
            poll_channel = self.data[guild_id]["poll_channel"]
        except KeyError:
            poll_channel = None
        if not poll_channel:
            await interaction.response.send_message(f"Set poll channel  to {channel.mention}",)
        else:
            await interaction.response.send_message(f"Changed poll channel to {channel.mention}")
        self.data[guild_id] = {"poll_channel": channel.id}


    def get_seconds(self, seconds:int=0, minutes:int=0, hours:int=0, days:int=0) -> int:
        hours += days * 24
        minutes += hours * 60
        seconds += minutes * 60
        return seconds


async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Poll(bot))