from typing import ClassVar

import discord
from discord import Member, User, app_commands
from discord.ui import Button

from core.bot import WinterDragon
from core.cogs import GroupCog
from base.mixins import LoggerMixin
from database.tables import ResultDuels


# TODO: change command /rps new
# dont dm user
# always create lobby first, unless dueled
# add logic for winning


class RpsButton(Button["RPSView"], LoggerMixin):
    def __init__(self, label: str, style: discord.ButtonStyle) -> None:
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self._view
        for button in view.children:
            button.disabled = True

        if not view.player_1:
            view.player_1 = interaction.user
        elif not view.player_2:
            view.player_2 = interaction.user

        if view.p1_choice is None:
            self._view.p1_choice = self.label
        elif view.p2_choice is None:
            self._view.p2_choice = self.label
        else:
            await view.calc_win(interaction)
        # return await super().callback(interaction)


# TODO: add 3 buttons, look at ticket system.
# Each button adds the player's choice,
# Set's player_1, and player_2 variable
# calcs results and posts them
class RPSView(discord.ui.View, LoggerMixin):
    """View created for rock paper scissors. Contains 3 buttons."""

    # children: list[RpsButton]
    p1_choice: str | None
    p2_choice: str | None
    player_1: User | Member | None
    player_2: User | Member | None

    def __init__(
        self,
        first_choice: str | None = None,
        second_choice: str | None = None,
        player_1: User | Member | None = None,
        player_2: User | Member | None = None,
    ) -> None:
        super().__init__()
        self.p1_choice = first_choice
        self.p2_choice = second_choice
        self.player_1 = player_1
        self.player_2 = player_2
        rock = RpsButton(label="Rock", style=discord.ButtonStyle.blurple)
        paper = RpsButton(label="Paper", style=discord.ButtonStyle.blurple)
        scissor = RpsButton(label="Scissors", style=discord.ButtonStyle.blurple)
        self.add_item(rock)
        self.add_item(paper)
        self.add_item(scissor)


    async def calc_win(self, interaction: discord.Interaction) -> None:
        self.logger.debug(f"{self.p1_choice=}, {self.p2_choice=}")
        if not self.p1_choice or not self.p2_choice:
            self.logger.critical(f"{self.calc_win.__name__} Called without both choices present.")
            return

        original = await interaction.original_response()
        await original.edit(content=f"{self.p1_choice=}, {self.p2_choice=}")

        if self.p1_choice == self.p2_choice:
            winner = None
            loser = None
        elif self.p1_choice == "rock":
            if self.p2_choice == "scissors":
                winner = self.player_1
                loser = self.player_2
            else:
                winner = self.player_2
                loser = self.player_1
        elif self.p1_choice == "paper":
            if self.p2_choice == "rock":
                winner = self.player_1
                loser = self.player_2
            else:
                winner = self.player_2
                loser = self.player_1
        elif self.p1_choice == "scissors":
            if self.p2_choice == "paper":
                winner = self.player_1
                loser = self.player_2
            else:
                winner = self.player_2
                loser = self.player_1

        with self.session as session:
            session.add(ResultDuels(
                # id=,
                game = "rps",
                player_1 = self.player_1,
                player_2 = self.player_2,
                winner = winner,
                loser = loser,
            ))
            session.commit()
        self.stop()



class RockPaperScissors(GroupCog):
    choices: ClassVar = ["rock", "paper", "scissor"]


    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="new",
        description="Start a rock paper, scissors game, which player can join",
    )
    async def slash_rps_new(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.send_message(f"{interaction.user.mention} started Rock, Paper, Scissors.", view=RPSView())
        # TODO: implement lobby system like Tic Tac Toe


    @app_commands.command(
        name="duel",
        description="Start a rock paper, scissors game, against specified player",
    )
    async def slash_rps_duel(
        self,
        interaction: discord.Interaction,
        choice: str,
        opponent: discord.Member,
    ) -> None:
        if choice not in self.choices:
            await interaction.response.send_message(f"Thats not a valid choice, must be one of {self.choices}", ephemeral=True)
        await interaction.response.send_message(
            content=f"{interaction.user.mention} dueled {opponent.mention} in Rock, Paper, Scissors. What's your choice?",
            view=RPSView(first_choice=choice, player_1=interaction.user, player_2=opponent),
        )
        # await interaction.response.send_message(f"{interaction.user.mention} started Rock, Paper, Scissors, what's your choice?", view=RPSView(first_choice=choice))
        # self.set_data(self.data)


    @slash_rps_duel.autocomplete("choice")
    async def rock_paper_scissors_autocomplete_choice(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:  # noqa: ARG002
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.choices
            if current.lower() in i.lower()
        ]


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(RockPaperScissors(bot))
