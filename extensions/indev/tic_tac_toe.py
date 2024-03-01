import asyncio
import itertools
import logging
import os
from functools import partial
from typing import Callable, TypedDict

import discord
import matplotlib.pyplot as plt
import sqlalchemy
from discord import app_commands

from _types.bot import WinterDragon
from _types.cogs import GroupCog
from _types.games.lobby import Lobby as GLobby
from tools.config_reader import config
from tools.database_tables import Game, Lobby, ResultDuels, Session, engine
from tools.ttt_ai import TicTacToeAi


GAME_NAME = "ttt"


class GameData(TypedDict):
    status: str
    member1: dict[str, int]
    member2: dict[str, int]


@app_commands.guild_only()
class TicTacToe(GroupCog):
    PLAYER1 = "Player 1"
    PLAYER1_JOINED = "Player 1 Join"
    PLAYER1_LEFT = "Player 1 Leave"

    PLAYER2 = "Player 2"
    PLAYER2_JOINED = "Player 2 Join"
    PLAYER2_LEFT = "Player 2 Leave"

    PIECHART_PATH = "./database/piechart/ttt"


    async def update_view(self, view: discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view


    @app_commands.checks.cooldown(2, 120)
    @app_commands.command(name="leaderboard", description="view tic-tac-toe stats")
    async def slash_leader_board(self, interaction: discord.Interaction) -> None:
        game_results = self.calculate_game_results(
            interaction.user.id,
            self.get_sql_leader_board(interaction.user.id),
        )
        if game_results is None:
            await interaction.response.send_message("No games found to display.", ephemeral=True)
            return

        self.create_pie_chart(game_results, interaction)
        chart = discord.File(f"{self.PIECHART_PATH}/{interaction.user.id}.png")
        await interaction.response.send_message(file=chart)
        chart.close()
        os.remove(f"{self.PIECHART_PATH}/{interaction.user.id}.png")


# Make own module for making graphs
    def make_autopct(self, values: list[float]) -> Callable[..., str]:
        def my_autopct(pct: float) -> str:
            total = sum(values)
            val = int(round(pct*total/100.0))
            return f"{val:d}  ({pct:.2f}%)"
        return my_autopct

    def create_pie_chart(self, game_results: dict[str, int], interaction: discord.Interaction) -> None:
        plt.figure(interaction.user.id)
        os.makedirs(self.PIECHART_PATH, exist_ok=True)

        for k, v in list(game_results.items()):
            if v == 0:
                game_results.pop(k)
        labels = game_results.keys()
        values = game_results.values()

        plt.suptitle(f"Total games: {sum(values)}")
        plt.pie(values, labels=labels, autopct=self.make_autopct(values))
        plt.savefig(f"{self.PIECHART_PATH}/{interaction.user.id}.png")
        plt.close(interaction.user.id)
## /\

    def get_sql_leader_board(self, interaction_user_id: int) -> list[ResultDuels]:
        with Session(engine) as session:
            result = session.query(ResultDuels).where(
                ResultDuels.game == GAME_NAME,
                sqlalchemy.or_(
                    ResultDuels.player_1 == interaction_user_id,
                    ResultDuels.player_2 == interaction_user_id,
            ))
            self.logger.debug(f"{result.all()=}")
            session.commit()
        return result.all()


    def calculate_game_results(
        self,
        interaction_user_id: int,
        results: list[ResultDuels] | None = None,
    ) -> dict[str, int] | None:
        self.logger.debug(f"Calculating stats for {interaction_user_id}")
        # BASE_GAME_RESULTS = {"total": 0, "abandoned": 0, "wins": 0, "losses": 0, "draws": 0}
        base_game_results = {"wins": 0, "losses": 0, "draws": 0}
        game_results = base_game_results.copy()

        if results is None:
            results = []

        for result in results:
            # game_results["total"] += 1
            if result.winner == interaction_user_id:
                game_results["wins"] += 1
            elif result.loser == interaction_user_id:
                game_results["losses"] += 1
            elif result.winner == 0 and result.loser == 0:
                game_results["draws"] += 1
            # else:
                # game_results["abandoned"] += 1

        self.logger.debug(f"{game_results=}, {results=}")
        return game_results if game_results != base_game_results else None


    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="new",
        description="Start a tic tac toe game/lobby, which players can join",
    )
    async def slash_new(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Lobby created!\nJoin here to start playing!")
        response_message = await interaction.original_response()

        lobby = GLobby(message=response_message, max_players=2)
        lobby.start_function = partial(
            self.start_game,
            interaction=interaction,
        )

        with Session(engine) as session:
            session.add(Lobby(
                id = response_message.id,
                game = GAME_NAME,
                status = "waiting",
            ))
            session.commit()


    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="challenge",
        description="Start a tic tac toe game, challenging a specific member/user",
    )
    async def slash_challenge(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.send_message(f"{interaction.user.mention} challenged {member.mention} in tic tac toe!")
        # game_data: GameData = {"status":"waiting", "member1":{"id": interaction.user.id}, "member2":{"id": member.id}}
        lobby = GLobby(message=None, max_players=2)
        lobby.players[0] = interaction.user
        lobby.players[1] = member
        await self.start_game(interaction=interaction, lobby=lobby) # , game_data=game_data

# # LOBBY start

#     async def button_handler(
#         self,
#         base_button_1: discord.ui.Button = None,
#         base_button_2: discord.ui.Button = None
#     ) -> tuple[discord.ui.Button, discord.ui.Button]:
#         if base_button_1 is None:
#             base_button_1 = Button(
#                 label = self.PLAYER1,
#                 style = discord.ButtonStyle.primary
#             )
#         if base_button_2 is None:
#             base_button_2 = Button(
#                 label = self.PLAYER2,
#                 style = discord.ButtonStyle.primary
#             )

#         button_1, button_2 = await self.button_join_or_leave(base_button_1, base_button_2)
#         return button_1, button_2


#     async def button_join_or_leave(
#         self,
#         player_1_btn: discord.ui.Button = None,
#         player_2_btn: discord.ui.Button = None
#     ) -> tuple[discord.ui.Button, discord.ui.Button]:
#         """Change button label based on join or leave condition

#         Args:
#             player_1_btn (discord.ui.Button): Button
#             player_2_btn (discord.ui.Button): Button

#         Returns:
#             tuple[discord.ui.Button, discord.ui.Button]: 2 buttons
#         """
#         if player_1_btn:
#             if player_1_btn.label == self.PLAYER1_JOINED:
#                 player_1_btn.label = self.PLAYER1_LEFT
#                 player_1_btn.style = discord.ButtonStyle.red
#                 player_1_btn.callback = self._leave_game_button_
#             elif player_1_btn.label in [self.PLAYER1_LEFT, self.PLAYER1]:
#                 player_1_btn.label = self.PLAYER1_JOINED
#                 player_1_btn.style = discord.ButtonStyle.green
#                 player_1_btn.callback = self._join_game_button

#         if player_2_btn:
#             if player_2_btn.label == self.PLAYER2_JOINED:
#                 player_2_btn.label = self.PLAYER2_LEFT
#                 player_2_btn.style = discord.ButtonStyle.red
#                 player_2_btn.callback = self._leave_game_button_
#             elif player_2_btn.label in [self.PLAYER2_LEFT, self.PLAYER2]:
#                 player_2_btn.label = self.PLAYER2_JOINED
#                 player_2_btn.style = discord.ButtonStyle.green
#                 player_2_btn.callback = self._join_game_button

#         return player_1_btn, player_2_btn


#     async def _join_game_button(self, interaction: discord.Interaction) -> None:
#         try:
#             # sourcery skip: remove-redundant-if
#             await interaction.response.defer()
#             original_interaction = await interaction.original_response()
#             lobby_msg = interaction.message.content
#             # user = session.query(User).where(User.lobby_id == lobby.id).first()
#             # Create new user when using fetch
#             # user: User = database_tables.User.fetch_user(interaction.user.id)

#             btn1 = Button(label = self.PLAYER1, style = discord.ButtonStyle.primary)
#             btn2 = Button(label = self.PLAYER2, style = discord.ButtonStyle.primary)

#             lobby_msg, _ = await self.join_association_handler(interaction, original_interaction, lobby_msg, btn1, btn2)
#             self.logger.debug(f"{lobby_msg=}")

#             if lobby_msg is None:
#                 return

#             button1, button2 = await self.button_handler(btn1, btn2)
#             view = View()
#             view = await self.update_view(view, button1, button2)
#             await interaction.edit_original_response(content=lobby_msg, view=view)
#         except Exception as e:
#             self.logger.exception(e)

#     # FIXME: bugfix, lobby reset bug, should be fixed with lobby code from _types
#     async def join_association_handler(
#         self,
#         interaction: discord.Interaction,
#         original_interaction: discord.Interaction,
#         lobby_msg: str,
#         btn1: discord.Button,
#         btn2: discord.Button
#     ) -> tuple[str, AUL]:
#         with Session(engine) as session:
#             lobby = session.query(Lobby).where(Lobby.id == original_interaction.id).first()
#             results = session.query(AUL).where(AUL.lobby_id == original_interaction.id)
#             associations = results.all()
#             self.logger.debug(f"User joined a game: {interaction.user=}, {lobby.id=}")
#             self.logger.debug(f"{associations=}, {lobby=}")

#             if not associations:
#                 self.logger.debug(f"adding first player {interaction.user} to lobby {lobby.id=}")
#                 btn1.label = self.PLAYER1_JOINED
#                 lobby_msg = f"{lobby_msg}\n{self.PLAYER1}: {interaction.user.mention}"
#                 session.add(AUL(
#                     lobby_id = lobby.id,
#                     user_id = interaction.user.id
#                 ))
#                 session.commit()
#             elif len(associations) == 1:
#                 self.logger.debug(f"adding extra player {interaction.user} to lobby {lobby.id=}, {associations=}")
#                 btn1.label = self.PLAYER1_JOINED
#                 btn2.label = self.PLAYER2_JOINED
#                 lobby_msg = f"{lobby_msg}\n{self.PLAYER2}: {interaction.user.mention}"
#                 session.add(AUL(
#                     lobby_id = lobby.id,
#                     user_id = interaction.user.id
#                 ))
#                 session.commit()

#             results = session.query(AUL).where(AUL.lobby_id == original_interaction.id)
#             associations = results.all()

#             if len(associations) == 2:
#                 player_1 = associations[0]
#                 player_2 = associations[1]
#                 self.logger.debug(f"2 players in {lobby.id=}, {associations=}")
#                 game_data = {"status": lobby.status, "member1": {"id": player_1.user_id}, "member2": {"id": player_2.user_id}}
#                 for i in associations:
#                     session.delete(i)
#                 session.delete(lobby)
#                 self.logger.debug(f"{game_data=}")
#                 lobby.status = "running"
#                 await self.start_game(interaction=interaction, game_data=game_data)
#                 session.commit()
#                 lobby_msg = None
#                 associations = None

#         self.logger.debug(f"{lobby=},\n {lobby_msg=},\n {associations=} <debug")
#         return lobby_msg, associations


#     async def leave_association_handler(
#             self,
#             interaction: discord.Interaction,
#             original_interaction: discord.Interaction
#         ) -> None:
#         with Session(engine) as session:
#             session.delete(session.query(AUL).where(AUL.lobby_id == original_interaction.id, AUL.user_id == interaction.user.id).first())
#             session.commit()


#     async def _leave_game_button_(self, interaction: discord.Interaction) -> None:
#         await interaction.response.defer()
#         original_interaction = await interaction.original_response()
#         with Session(engine) as session:
#             results = session.query(AUL).where(AUL.lobby_id == original_interaction.id)
#             associations = results.all()

#         self.logger.debug(f"User left a game: {interaction.user=}, {associations=}")

#         btn1 = Button(label=self.PLAYER1, style=discord.ButtonStyle.primary)
#         btn2 = Button(label=self.PLAYER2, style=discord.ButtonStyle.primary)
#         lobby_msg = interaction.message.content

#         if len(associations) == 2:
#         # if game_data["member2"]["id"] == interaction.user.id:
#             await self.leave_association_handler(interaction, original_interaction)
#             # game_data["member2"]["id"] = 0
#             btn1.label = self.PLAYER1_JOINED
#             btn2.label = self.PLAYER2_LEFT
#             lobby_msg = lobby_msg.replace(f"\n{self.PLAYER2}: {interaction.user.mention}", "")
#         elif len(associations) == 1:
#         # elif game_data["member1"]["id"] == interaction.user.id:
#             await self.leave_association_handler(interaction, original_interaction)
#             # game_data["member1"]["id"] = 0
#             btn1.label = self.PLAYER1_LEFT
#             lobby_msg = lobby_msg.replace(f"\n{self.PLAYER1}: {interaction.user.mention}", "")

#         button1, button2 = await self.button_handler(btn1, btn2)
#         view = View()
#         view = await self.update_view(view, button1, button2)
#         await interaction.edit_original_response(content=lobby_msg, view=view)

# # LOBBY end



# GAME start

    async def start_game(self, interaction: discord.Interaction, lobby: GLobby) -> None:
        p1 = lobby.players[0]
        p2 = lobby.players[1]
        self.logger.debug(f"Starting game between {p1.mention, p2.mention}")
        await interaction.edit_original_response(
            content=f"Game has started!, It is {p1.mention}'s Turn",
            view=TicTacToeGame(
                player_one = p1,
                player_two = p2,
            ),
        )


# Modified code from https://github.com/Rapptz/discord.py/blob/master/examples/views/tic_tac_toe.py
# To avoid other players intervening


class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, x: int, y: int) -> None:
        # A label is required, but we don't need one so a zero-width space is used, '\u200b'
        # The row parameter tells the View which row to place the button under.
        # A View can only contain up to 5 rows -- each row can only have 5 buttons.
        # Since a Tic Tac Toe grid is 3x3 that means we have 3 rows and 3 columns.
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.x = x
        self.y = y

    # This function is called whenever this button is pressed
    async def callback(self, interaction: discord.Interaction, from_ai: bool=False) -> None:
        view: TicTacToeGame = self.view
        if interaction.user.id not in [view.player_x.id, view.player_o.id]:
            await interaction.response.send_message("You may not play in this game", ephemeral=True)
            return

        if interaction.user.id != view.current_player and not from_ai:
            await interaction.response.send_message("It's not your turn", ephemeral=True)
            return

        assert self.view is not None
        state = view.board[self.y][self.x]
        if state in [view.player_x.id, view.player_o.id] and from_ai:
            await view.make_bot_move(interaction)
            return

        if view.current_player == view.player_x.id:
            self.style = discord.ButtonStyle.danger
            self.label = "X"
            view.board[self.y][self.x] = view.player_x.id
            view.current_player = view.player_o.id
            content = f"It is now {view.player_o.mention or 'O'}'s turn"
        elif view.current_player == view.player_o.id:
            self.style = discord.ButtonStyle.success
            self.label = "O"
            view.board[self.y][self.x] = view.player_o.id
            view.current_player = view.player_x.id
            content = f"It is now {view.player_x.mention or 'X'}'s turn"

        self.disabled = True
        winner = view.check_board_winner()
        self.logger.debug(f"{winner=}")

        if winner is not None:
            if winner == view.player_x.id:
                content = f'{view.player_x.mention or "X"} won!'
            elif winner == view.player_o.id:
                content = f'{view.player_o.mention or "O"} won!'
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        if from_ai:
            await asyncio.sleep(1)
            await interaction.edit_original_response(content=content, view=view)
        else:
            await interaction.response.edit_message(content=content, view=view)

        if (
            view.is_vs_bot
            and not from_ai
        ):
            self.logger.debug("Before TTT AI Move")
            await view.make_bot_move(interaction)
            self.logger.debug("After TTT AI Move")



# This is our actual board View
# TODO: Move game data to database
class TicTacToeGame(discord.ui.View):
    player_x: discord.Member
    player_o: discord.Member
    Tie = 2
    children: list[TicTacToeButton] # type: ignore


    def __init__(self, player_one: discord.Member, player_two: discord.Member, game_data: GameData) -> None:
        super().__init__()
        self.player_x = player_one
        self.player_o = player_two
        self.current_player = self.player_x.id
        self.game_data = game_data
        self.logger = logging.getLogger(f"{config['Main']['bot_name']}.{self.__class__.__name__}")
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        # Our board is made up of 3 by 3 TicTacToeButtons
        # The TicTacToeButton maintains the callbacks and helps steer
        # the actual game.
        for x, y in itertools.product(range(3), range(3)):
            self.add_item(TicTacToeButton(x, y))


    @property
    def is_vs_bot(self) -> bool:
        return any([self.player_o.bot, self.player_x.bot])


    async def make_bot_move(self, interaction: discord.Interaction) -> None:
        """Make the bot/ai do a move!"""
        ai = TicTacToeAi(
            o=self.player_o.id,
            x=self.player_x.id,
            board=self.board,
        )

        if self.player_o.bot:
            row, column = ai.get_best_move(self.player_o.id)
            self.logger.debug(f"best move for {self.player_o} = {row, column}")
            # self.current_player = self.player_x.id
        elif self.player_x.bot:
            row, column = ai.get_best_move(self.player_x.id)
            self.logger.debug(f"best move for {self.player_x} = {row, column}")
            # self.current_player = self.player_o.id
        else:
            msg = f"HOW DID WE GET HERE?: Expected Bot User, but got {self.player_o} and {self.player_x}"
            raise ValueError(msg)

        for button in self.children:
            if button.y == row and button.x == column:
                if button.disabled:
                    self.logger.warning("Button is disabled!")
                    return
                await button.callback(interaction, from_ai=True)
                break

        self.logger.debug("After button callback ai")


    # This method checks for the board winner -- it is used by the TicTacToeButton
    def check_board_winner(self) -> int | None:
        duel_result = None
        game_result = None

        # Check horizontal
        for across in self.board:
            value = sum(across)
            if value == (self.player_x.id*3):
                self.logger.debug(f"player X: {self.player_x} won straight on {across}")
                duel_result = ResultDuels(
                    player_1 = self.player_x.id,
                    player_2 = self.player_o.id,
                    winner = self.player_x.id,
                    loser = self.player_o.id,
                )
                # self.game_data["status"] = "finished-player1"
                game_result = self.player_x.id
            elif value == (self.player_o.id*3):
                self.logger.debug(f"player O: {self.player_o} won straight on {across}")
                duel_result = ResultDuels(
                    player_1 = self.player_o.id,
                    player_2 = self.player_x.id,
                    winner = self.player_o.id,
                    loser = self.player_x.id,
                )
                # self.game_data["status"] = "finished-player2"
                game_result = self.player_o.id

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == (self.player_x.id*3):
                self.logger.debug(f"player X: {self.player_x} won vertical on column {line}")
                duel_result = ResultDuels(
                    player_1 = self.player_x.id,
                    player_2 = self.player_o.id,
                    winner = self.player_x.id,
                    loser = self.player_o.id,
                )
                # self.game_data["status"] = "finished-player1"
                game_result = self.player_x.id
            elif value == (self.player_o.id*3):
                self.logger.debug(f"player O: {self.player_o} won vertical on column {line}")
                duel_result = ResultDuels(
                    player_1 = self.player_o.id,
                    player_2 = self.player_x.id,
                    winner = self.player_o.id,
                    loser = self.player_x.id,
                )
                # self.game_data["status"] = "finished-player2"
                game_result = self.player_o.id

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0] # /
        if diag == (self.player_x.id*3):
            self.logger.debug(f"player X: {self.player_x} won diagonally /")
            duel_result = ResultDuels(
                player_1 = self.player_x.id,
                player_2 = self.player_o.id,
                winner = self.player_x.id,
                loser = self.player_o.id,
            )
            # self.game_data["status"] = "finished-player1"
            game_result = self.player_x.id
        elif diag == (self.player_o.id*3):
            self.logger.debug(f"player O: {self.player_o} won diagonally /")
            duel_result = ResultDuels(
                player_1 = self.player_o.id,
                player_2 = self.player_x.id,
                winner = self.player_o.id,
                loser = self.player_x.id,
            )
            # self.game_data["status"] = "finished-player2"
            game_result = self.player_o.id

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2] # \
        if diag == (self.player_x.id*3):
            self.logger.debug(f"player X: {self.player_x} won diagonally \\ ")
            duel_result = ResultDuels(
                player_1 = self.player_x.id,
                player_2 = self.player_o.id,
                winner = self.player_x.id,
                loser = self.player_o.id,
            )
            # self.game_data["status"] = "finished-player1"
            game_result = self.player_x.id
        elif diag == (self.player_o.id*3):
            self.logger.debug(f"player O: {self.player_o} won diagonally \\ ")
            duel_result = ResultDuels(
                player_1 = self.player_o.id,
                player_2 = self.player_x.id,
                winner = self.player_o.id,
                loser = self.player_x.id,
            )
            # self.game_data["status"] = "finished-player2"
            game_result = self.player_o.id

        game = Game.fetch_game_by_name(GAME_NAME)

        self.logger.debug(f"{game_result=}, {duel_result=}")
        if game_result is not None:
            with Session(engine) as session:
                self.logger.debug(f"There is a winner: {game_result=}")
                duel_result.game = game.id
                session.add(duel_result)
                session.commit()
                self.logger.debug("Returning winner")
            return game_result

        # if any cell is empty, and no winner is determined, return None
        if any(i == 0 for row in self.board for i in row):
            return None

        # self.game_data["status"] = "finished-draw"
        with Session(engine) as session:
            self.logger.debug("Adding tie to DB")
            session.add(ResultDuels(
                game = game.id,
                player_1 = self.player_o.id,
                player_2 = self.player_x.id,
                winner = 0,
                loser = 0,
            ))
            session.commit()
        return self.Tie


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(TicTacToe(bot)) # type: ignore
