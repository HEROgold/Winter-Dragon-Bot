import logging
import discord
import os
import json
import random
from discord.ext import commands
from discord import app_commands
import rainbow

class nhie(commands.Cog):
    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.DBLocation = "./Database/NHIE.json"
        self.setup_db()

    def setup_db(self):
        if not os.path.exists(self.DBLocation): 
            with open(self.DBLocation, "w") as f:
                data = {"game_id": 0, "questions": {}}
                questions = data["questions"]
                for question_id, question in enumerate(nhie_default_questions): 
                    data["questions"][question_id] = nhie_default_questions[question_id]
                json.dump(data, f)
                f.close
                logging.info("NHIE Json Created.")
        else:
            logging.info("NHIE Json Loaded.")

    async def get_data(self) -> dict[str,int|dict[str, str]]:
        with open(self.DBLocation, 'r') as f:
            data = json.load(f)
        return data

    async def set_data(self, data):
        with open(self.DBLocation,'w') as f:
            json.dump(data, f)

    @app_commands.command(
        name="never_have_i_ever",
        description = "Use this to get a never have i ever question, that you can reply to"
    )
    @app_commands.guild_only()
    @commands.cooldown(1, 2)
    async def slash_nhie(self, interaction:discord.Interaction):
        data = await self.get_data() 
        game_id = data["game_id"]
        game_id += 1
        data["game_id"] = game_id
        d:dict = data["questions"]
        questions = [v for k, v in d.items()]
        await self.set_data(data) 
        question = random.choice(questions)
        emb = discord.Embed(title=f"Never Have I Ever #{game_id}", description=question, color=random.choice(rainbow.RAINBOW))
        emb.add_field(name="I Have", value="✅")
        emb.add_field(name="Never", value="⛔")
        send_msg = await interaction.channel.send(embed=emb)
        await send_msg.add_reaction("✅")
        await send_msg.add_reaction("⛔")
        await interaction.response.send_message("Question send", ephemeral=True)

    @app_commands.command(
        name = "never_have_i_ever_add",
        description="Lets you add a Never Have I Ever question"
        )
    async def slash_nhieadd(self, interaction:discord.Interaction, nhie_question:str):
        data = await self.get_data()
        if "add" not in data:
            data["add"] = {}
        if "add" in data:
            data["add"][nhie_question] = False
        await self.set_data(data)
        await interaction.response.send_message(f"The question ```{nhie_question}``` is added, it will be verified later.", ephemeral=True)

    @app_commands.command(
        name = "nhie_add_add_verified",
        description = "Add all questions stored in the NHIE database file, to the questions data section.")
    async def slash_nvie_add_verified(self, interaction:discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            raise commands.NotOwner
        data = await self.get_data()
        d = data["add"]
        for k1, v1 in list(d.items()):
            if v1 == True:
                d2 = data["questions"]
                for k2, v2 in d2.items():
                    question_id = int(k2)
                question_id += 1
                data["questions"][question_id] = d.pop(k1)
        await self.set_data(data)
        await interaction.response.send_message("Added all verified questions", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(nhie(bot))

nhie_default_questions = [
"Never have I ever gone skinny dipping.",
"Never have I ever gone on a blind date.",
"Never have I ever creeped an ex on social media.",
"Never have I ever been hungover.",
"Never have I ever kissed my best friend.",
"Never have I ever ghosted someone.",
"Never have I ever gotten a speeding ticket.",
"Never have I ever slid into someone's DMs.",
"Never have I ever dined and dashed.",
"Never have I ever used a fake ID.",
"Never have I ever had a crush on a teacher.",
"Never have I ever been in love.",
"Never have I ever made out in a public place.",
"Never have I ever gotten into a physical fight.",
"Never have I ever had an alcoholic drink.",
"Never have I ever played spin the bottle.",
"Never have I ever snooped through someone's phone.",
"Never have I ever snuck into a movie theater.",
"Never have I ever kissed a friend's ex.",
'Never have I ever told someone "I love you" without meaning it.',
"Never have I ever been called a player.",
"Never have I ever smoked a cigarette.",
"Never have I ever given a lap dance.",
"Never have I ever gotten a lap dance.",
"Never have I ever cheated on a test.",
"Never have I ever used a dating app.",
"Never have I ever kissed more than one person in 24 hours.",
"Never have I ever cheated on someone.",
"Never have I ever been cheated on.",
"Never have I ever sent a racy text to the wrong person.",
"Never have I ever had a negative bank account balance.",
"Never have I ever played strip poker.",
"Never have I ever been arrested.",
"Never have I ever been expelled.",
"Never have I ever stolen anything.",
"Never have I ever gotten a hickey.",
"Never have I ever been fired.",
"Never have I ever made out in a movie theater.",
"Never have I ever dated someone older than me.",
"Never have I ever dated someone younger than me.",
"Never have I ever broken the law.",
"Never have I ever been to a nude beach.",
"Never have I stood a date up.",
"Never have I ever stayed in a relationship that I really wasn`t feeling.",
"Never have I ever given someone a fake phone number.",
"Never have I ever lied to someone in this room.",
"Never have I ever broken up with someone over text.",
"Never have I ever had a crush on an SO`s best friend.",
"Never have I ever shoplifted.",
"Never have I ever seen a ghost.",
"Never have I told a secret I wasn`t supposed to share.",
"Never have I ever had a friend with benefits.",
"Never have I ever intentionally started a fight between other people.",
"Never have I ever dated more than one person at once.",
"Never have I ever spent money that wasn`t mine to spend.",
"Never have I ever had a relationship last less than a month.",
"Never have I ever had a relationship last longer than a year.",
"Never have I ever gotten an unexpected piercing.",
"Never have I ever found a dumb excuse to text an ex.",
"Never have I ever fallen in love at first sight.",
"Never have I ever kissed someone I just met.",
"Never have I ever kept a crush secret from people in this room.",
"Never have I ever been in love with someone without them knowing.",
"Never have I ever been in an open relationship.",
"Never have I ever fantasized about getting back with an ex.",
"Never have I ever helped a friend lie by being their alibi.",
"Never have I ever seriously thought about marrying someone.",
"Never have I ever had a totally online relationship.",
"Never have I ever flirted just to get something I wanted.",
"Never have I ever tried guessing someone`s password.",
"Never have I ever been caught lying.",
    ];