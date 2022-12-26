import logging
import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import config

class get_message(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot:commands.Bot = bot
        self.DBLocation = "./Database/Message.json"
        # Create database if it doesn't exist, else load it
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = {}
                json.dump(data, f)
                f.close
                logging.info("Message Json Created.")
        else:
            logging.info("Message Json Loaded.")

    # Helper functions to laod and update database
    async def get_data(self) -> dict[str, dict[str, dict[str, str]]]:
        with open(self.DBLocation, 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data:dict):
        with open(self.DBLocation,'w') as f:
            json.dump(data, f)

    @app_commands.command(name = "get_messages", description = f"get and store the last {config.message.limit} messages, in each channel from this server!")
    async def slash_get_message(self, interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = await self.get_data()
        guild = interaction.guild
        guild_id = str(guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        for channel in interaction.guild.text_channels:
            channel_id = str(channel.id)
            if channel_id not in data[guild_id]:
                data[guild_id][channel_id] = {}
            async for message in channel.history(limit=config.message.limit):
                if str(message.id) in data[guild_id][channel_id]:
                    break
                if message.content in ["", "[Original Message Deleted]"]:
                    # Skipt empty contents (I.e. Bot embeds etc.)
                    continue
                data[guild_id][channel_id][message.id] = str(message.content)
            if not data[guild_id][channel_id]:
                # Clean-up data if channel has no messages.
                del data[guild_id][channel_id]
        await self.set_data(data)
        await interaction.followup.send("Updated my database!", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(get_message(bot))