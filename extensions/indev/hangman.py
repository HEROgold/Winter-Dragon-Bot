import logging
import random
from typing import Callable

import discord  # type: ignore
from discord import app_commands
from discord.ext import commands
import requests

import config
from tools.database_tables import ResultMassiveMultiplayer as ResultMM
from tools.database_tables import AssociationUserHangman as AUH
from tools.database_tables import Hangman as HangmanDb
from tools.database_tables import Game, Session, engine


HANGMEN = [
    """
 ------
|        |
|   
|   
|   
|   
|   
|   
----------
"""
    ,
"""
 ------
|       |
|       0
|   
|   
|   
|   
|   
----------
"""
   ,
"""
 ------
|        |
|        0
|        +
|   
|   
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|       -+
|   
|   
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|       -+-
|   
|   
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|      /-+-
|   
|   
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|      /-+-/
|   
|   
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|      /-+-/
|        |
|   
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|      /-+-/
|        |
|        |
|   
|   
----------
"""
    ,
"""
 ------
|        |
|        0
|      /-+-/
|        |
|        |
|       |
|       |
----------
"""
    ,
"""
 ------
|        |
|        0
|      /-+-/
|        |
|        |
|       | |
|       | |
----------
"""
]


def create_hangman(guess_amount: int) -> str:
    return HANGMEN[guess_amount]


class HangmanButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle) -> None:
        super().__init__(label=label, style=style)
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.send_modal(SubmitLetter())
        except Exception as e:
            self.logger.exception(e)


# TODO: Cleanup code

class SubmitLetter(discord.ui.Modal, title="Submit Letter"):
    letter = discord.ui.TextInput(label="Letter", min_length=1, max_length=1)


    async def on_submit(self, interaction: discord.Interaction) -> None:
        # sourcery skip: low-code-quality
        logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        logger.debug(f"Submitting {self.letter.value=}")

        # Add full game logic here, and use DB to keep track of chosen letters, progress etc.
        with Session(engine) as session:
            hangman_db = session.query(HangmanDb).where(HangmanDb.id == interaction.message.id).first()
            if hangman_db is None:
                logger.debug("Hangman is empty, creating new one.")
                r_word = random.choice(requests.get("https://www.mit.edu/~ecprice/wordlist.10000").text.splitlines())
                # r_word = "test word"
                logger.debug(f"{r_word=}")

                hangman_db = HangmanDb(
                    id = interaction.message.id,
                    word = r_word,
                    letters = ""
                )
                session.add(hangman_db)
            else:
                logger.debug("Hangman game found")

            if self.letter.value in hangman_db.letters:
                logger.debug(f"Already chosen: {self.letter.value=}, {interaction.user=}")
                await interaction.response.send_message("Letter already chosen, please choose another", ephemeral=True)

            logger.debug(f"Adding {self.letter.value=}")
            # Add AUH if new player
            # Check when answer is good or wrong, then give/deduct points
            player = session.query(AUH).where(
                AUH.hangman_id == interaction.message.id,
                AUH.user_id == interaction.user.id
            ).first()

            if player is None:
                player = AUH(
                    hangman_id = interaction.message.id,
                    user_id = interaction.user.id,
                    score = 0
                )
                session.add(player)

            # Check hangman_db.letters from before, and after adding self.letter.value
            # to check for good vs bad answer
            wrong_before = [
                i for i in hangman_db.letters
                if i not in hangman_db.word
            ]

            hangman_db.letters += self.letter.value

            wrong_after = [
                i for i in hangman_db.letters
                if i not in hangman_db.word
            ]

            hidden_word = "".join(
                i if i in hangman_db.letters else "-" 
                for i in hangman_db.word
            )

            # Stop early and lose after 10 faulty guesses
            if len(wrong_after) >= 10:
                await interaction.response.edit_message(
                    content=f"Game Lost...\nGuesses: {hidden_word}\n Word: {hangman_db.word}\n{hangman}`\nLetters: {hangman_db.letters}",
                    view=None
                )
                return

            try:
                player.score += 2 if wrong_before == wrong_after else -1
            except TypeError:
                player.score = 2 if wrong_before == wrong_after else 1

            # Check if all letters are in the word.
            checks: list[bool] = []
            for i in hangman_db.word:
                if i in hangman_db.letters:
                    checks.append(True)
                else:
                    checks.append(False)
            logger.debug(f"{checks=}")

            hangman = create_hangman(guess_amount=len(wrong_after))

            if not all(checks):
                await interaction.response.edit_message(content=f"Word: {hidden_word}\n{hangman}\nLetters: {hangman_db.letters}")
                session.commit()
                return

            # Fetch all players that played,
            # Push results to results table
            # then delete association table data for that player.
            hangman_players = session.query(AUH).where(AUH.hangman_id == interaction.message.id).all()
            logger.debug(f"{hangman_players=}")
            try:
                sort_key: Callable[[AUH]] = lambda x: x.score
                hangman_players.sort(key=sort_key)
            except AttributeError as e:
                logger.exception(f"{e}")

            placement = 0
            for i, j in enumerate(hangman_players):
                placement = i+1
                if j.user_id == interaction.user.id:
                    break

            session.add(ResultMM(
                game = session.query(Game).where(Game.name == "hangman").first().id,
                user_id = interaction.user.id,
                placement = placement
            ))

            for i in hangman_players:
                session.delete(i)

            # Edit message, change status and end game
            await interaction.response.edit_message(
                content=f"Game Won!\nWord: {hangman_db.word}\n{hangman}\nLetters: {hangman_db.letters}",
                view = None
            )
            session.commit()


class Hangman(commands.GroupCog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")

        with Session(engine) as session:
            self.game = session.query(Game).where(Game.name == "hangman").first()
            if self.game is None:
                session.add(Game(
                    name = "hangman"
                ))
            session.commit()


    # Hangman_GROUP = app_commands.Group(name="HangmanGroup", description="Hangman")
    # @Hangman_GROUP.command()


    @app_commands.command(name="start", description="Hangman")
    async def slash_Hangman(self, interaction: discord.Interaction) -> None:
        """Hangman"""
        view = discord.ui.View()
        btn = HangmanButton(label = "Add Letter", style = discord.ButtonStyle.primary)
        view.add_item(btn)
        await interaction.response.send_message(f"{HANGMEN[0]}", view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Hangman(bot))  # type: ignore
