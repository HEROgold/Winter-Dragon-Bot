import itertools
import logging
import os
import pickle
import random
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

import config
import rainbow
from tools import dragon_database

# TODO: Add ai if bot is challenged?

@app_commands.guild_only()
class TicTacToe(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.pkl"
            self.setup_db_file()

    def setup_db_file(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "wb") as f:
                data = self.data
                pickle.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME}.pkl Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME}.pkl File Exists.")

    def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = db.get_data(self.DATABASE_NAME)
        elif os.path.getsize(self.DBLocation) > 0:
            with open(self.DBLocation, "rb") as f:
                data = pickle.load(f)
        return data

    def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "wb") as f:
                pickle.dump(data, f)

    async def cog_load(self) -> None:
        if not self.data:
            self.data = self.get_data()
        if not self.data:
            self.data = {
                "DUMMY": {
                    "status": "waiting",
                    "member1": {"id": 0},
                    "member2": {"id": 0},
                    }
                }

    async def cog_unload(self) -> None:
        self.set_data(self.data)

    async def update_view(self, view:discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view

    @app_commands.checks.cooldown(2, 120)
    @app_commands.command(
        name = "stats",
        description="view tic-tac-toe stats"
    )
    async def slash_leader_board(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = self.get_data()
        game_restults = None
        for game_data in self.data.values():
            status:str = game_data["status"]
            game_restults = {"total":0, "abandoned":0, "\u200b":"\u200b", "wins":0, "losses":0, "draws":0}
            user_id = str(interaction.user.id)

            # Determine abandoned/ongoing and draws
            if status in {"running", "waiting"}:
                game_restults["abandoned"] +=1
            elif status == "finished-draw":
                game_restults["draws"] += 1

            # Determine wins and losses
            if user_id == game_data["member1"]["id"]:
                if status == "finished-player1":
                    game_restults["wins"] += 1
                elif status == "finished-player2":
                    game_restults["losses"] += 1
            if user_id == game_data["member2"]["id"]:
                if status == "finished-player1":
                    game_restults["losses"] += 1
                elif status == "finished-player2":
                    game_restults["wins"] += 1

            game_restults["total"] += 1

        if not game_restults:
            await interaction.response.send_message("No gamestats to display.", ephemeral=True)
            return

        embed=discord.Embed(title="Stats", description="Your Tic Tac Toe Stats", color=random.choice(rainbow.RAINBOW))
        for name, value in game_restults.items():
            embed.add_field(name=name, value=value, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="new",
        description="Start a tic tac toe game/lobby, which players can join"
    )
    async def slash_tic_tac_toe(self, interaction: discord.Interaction) -> None:
        button1, button2 = await self.button_handler()
        view = View()
        view = await self.update_view(view, button1, button2)
        await interaction.response.send_message("Lobby created!\nJoin here to start playing!", view=view)
        resp_msg = await interaction.original_response()
        self.data[str(resp_msg.id)] = {"status":"waiting", "member1":{"id":0}, "member2":{"id":0}}
        self.set_data(self.data)

    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="challenge",
        description="Start a tic tac toe game, challenging a specific member/user"
    )
    async def slash_challenge(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if member.bot is True:
            await interaction.response.send_message("Bot's cannot play.")
        await interaction.response.send_message(f"{interaction.user.mention} challenged {member.mention} in tic tac toe!")
        resp_msg = await interaction.original_response()
        game_data = {"status":"waiting", "member1":{"id":interaction.user.id}, "member2":{"id":member.id}}
        self.data[str(resp_msg.id)] = game_data
        await self.start_game(interaction=interaction, game_data=game_data)

# LOBBY start

    async def button_handler(self, base_button_1:discord.ui.Button=None, base_button_2:discord.ui.Button=None) -> tuple[discord.ui.Button, discord.ui.Button]:
        if base_button_1 is None:
            base_button_1 = Button(
                label="Player 1",
                style=discord.ButtonStyle.primary
            )
        if base_button_2 is None:
            base_button_2 = Button(
                label="Player 2",
                style=discord.ButtonStyle.primary
            )

        button_1, button_2 = await self.button_join_or_leave(base_button_1, base_button_2)
        return button_1, button_2

    async def button_join_or_leave(self, player_1_btn:discord.ui.Button=None, player_2_btn:discord.ui.Button=None) -> tuple[discord.ui.Button, discord.ui.Button]:
        """Change button label based on join or leave condition

        Args:
            player_1_btn (discord.ui.Button): Button
            player_2_btn (discord.ui.Button): Button

        Returns:
            tuple[discord.ui.Button, discord.ui.Button]: 2 buttons
        """
        if player_1_btn:
            if player_1_btn.label == "Player 1 Join":
                player_1_btn.label = "Player 1 Leave"
                player_1_btn.style = discord.ButtonStyle.red
                player_1_btn.callback = self._leave_game_button_
            elif player_1_btn.label in ["Player 1 Leave", "Player 1"]:
                player_1_btn.label = "Player 1 Join"
                player_1_btn.style = discord.ButtonStyle.green
                player_1_btn.callback = self._join_game_button_

        if player_2_btn:
            if player_2_btn.label == "Player 2 Join":
                player_2_btn.label = "Player 2 Leave"
                player_2_btn.style = discord.ButtonStyle.red
                player_2_btn.callback = self._leave_game_button_
            elif player_2_btn.label in ["Player 2 Leave", "Player 2"]:
                player_2_btn.label = "Player 2 Join"
                player_2_btn.style = discord.ButtonStyle.green
                player_2_btn.callback = self._join_game_button_

        return player_1_btn, player_2_btn

    async def _join_game_button_(self, interaction:discord.Interaction) -> None:
        await interaction.response.defer()
        original_interaction = await interaction.original_response()
        for game_id, game_data in self.data.items():
            if game_id != str(original_interaction.id):
                continue
            btn1 = Button(label="Player 1", style=discord.ButtonStyle.primary)
            btn2 = Button(label="Player 2", style=discord.ButtonStyle.primary)
            lobby_msg = interaction.message.content
            if game_data["member1"]["id"] == 0:
                game_data["member1"]["id"] = interaction.user.id
                btn1.label = "Player 1 Join"
                lobby_msg = f"{lobby_msg}\nPlayer 1: {interaction.user.mention}"
            elif game_data["member2"]["id"] == 0 and game_data["member1"]["id"] != interaction.user.id:
                game_data["member2"]["id"] = interaction.user.id
                btn1.label = "Player 1 Join"
                btn2.label = "Player 2 Join"
                lobby_msg = f"{lobby_msg}\nPlayer 2: {interaction.user.mention}"
            else:
                continue
            self.logger.debug(f"User joined a game: user=`{interaction.user}, game=`{game_data}")
            button1, button2 = await self.button_handler(btn1, btn2)
            view = View()
            view = await self.update_view(view, button1, button2)
            await interaction.edit_original_response(content=lobby_msg, view=view)
            if game_data["member1"]["id"] != 0 and game_data["member2"]["id"] != 0 :
                await self.start_game(interaction=interaction, game_data=game_data)

    async def _leave_game_button_(self, interaction:discord.Interaction) -> None:
        await interaction.response.defer()
        original_interaction = await interaction.original_response()
        for game_id, game_data in self.data.items():
            if game_id != str(original_interaction.id):
                continue
            btn1 = Button(label="Player 1", style=discord.ButtonStyle.primary)
            btn2 = Button(label="Player 2", style=discord.ButtonStyle.primary)
            lobby_msg = interaction.message.content
            if game_data["member2"]["id"] == interaction.user.id:
                game_data["member2"]["id"] = 0
                btn1.label = "Player 1 Join"
                btn2.label = "Player 2 Leave"
                lobby_msg = lobby_msg.replace(f"\nPlayer 2: {interaction.user.mention}", "")
            elif game_data["member1"]["id"] == interaction.user.id:
                game_data["member1"]["id"] = 0
                btn1.label = "Player 1 Leave"
                lobby_msg = lobby_msg.replace(f"\nPlayer 1: {interaction.user.mention}", "")
            else:
                continue
            self.logger.debug(f"User left a game: user=`{interaction.user}, game=`{game_data}")
            button1, button2 = await self.button_handler(btn1, btn2)
            view = View()
            view = await self.update_view(view, button1, button2)
            await interaction.edit_original_response(content=lobby_msg, view=view)

# LOBBY end

# GAME start

    async def start_game(self, interaction:discord.Interaction, game_data:dict=None) -> None:
        game_data["status"] = "running"
        all_members = self.bot.get_all_members()
        p1 = discord.utils.get(all_members, id=game_data["member1"]["id"])
        p2 = discord.utils.get(all_members, id=game_data["member2"]["id"])
        self.logger.debug(f"Starting game between {p1.mention, p2.mention}")
        await interaction.edit_original_response(
            content=f"Game has started!, It is {p1.mention}'s Turn",
            view=TicTacToeGame(
                player_one=p1,
                player_two=p2,
                game_data=game_data
            )
        )
        self.set_data(self.data)

# Modified code from https://github.com/Rapptz/discord.py/blob/master/examples/views/tic_tac_toe.py
# To avoid other players intervening

class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int) -> None:
        # A label is required, but we don't need one so a zero-width space is used, '\u200b'
        # The row parameter tells the View which row to place the button under.
        # A View can only contain up to 5 rows -- each row can only have 5 buttons.
        # Since a Tic Tac Toe grid is 3x3 that means we have 3 rows and 3 columns.
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
        self.x = x
        self.y = y

    # This function is called whenever this button is pressed
    async def callback(self, interaction: discord.Interaction) -> None:
        view: TicTacToeGame = self.view
        if interaction.user.id not in [view.player_x.id, view.player_o.id]:
            await interaction.response.send_message("You may not play in this game", ephemeral=True)
            return
        elif interaction.user.id != view.current_player:
            await interaction.response.send_message("It's not your turn", ephemeral=True)
            return
        assert self.view is not None
        state = view.board[self.y][self.x]
        if state in (view.player_x.id, view.player_o.id):
            return

        if view.current_player == view.player_x.id:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            view.board[self.y][self.x] = view.player_x.id
            view.current_player = view.player_o.id
            content = f"It is now {view.player_o.mention or 'O'}'s turn"
        elif view.current_player == view.player_o.id:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            view.board[self.y][self.x] = view.player_o.id
            view.current_player = view.player_x.id
            content = f"It is now {view.player_x.mention or 'X'}'s turn"

        self.disabled = True
        winner = view.check_board_winner()

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

        await interaction.response.edit_message(content=content, view=view)


# This is our actual board View
class TicTacToeGame(discord.ui.View):
    player_x: discord.Member
    player_o: discord.Member
    Tie = 2
    children: List[TicTacToeButton] # type: ignore

    def __init__(self, player_one: discord.Member, player_two: discord.Member, game_data: dict) -> None:
        super().__init__()
        self.player_x = player_one
        self.player_o = player_two
        self.current_player = self.player_x.id
        self.game_data = game_data
        self.logger = logging.getLogger(f"{config.Main.BOT_NAME}.{self.__class__.__name__}")
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

    # This method checks for the board winner -- it is used by the TicTacToeButton
    def check_board_winner(self) -> int | None:
        for across in self.board:
            value = sum(across)
            if value == (self.player_x.id*3):
                self.logger.debug(f"player {self.player_x} won straight on {across}")
                self.game_data["status"] = "finished-player1"
                return self.player_x.id
            elif value == (self.player_o.id*3):
                self.logger.debug(f"player {self.player_o} won straight on {across}")
                self.game_data["status"] = "finished-player2"
                return self.player_o.id

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == (self.player_x.id*3):
                self.logger.debug(f"player {self.player_x} won vertical on column {line}")
                self.game_data["status"] = "finished-player1"
                return self.player_x.id
            elif value == (self.player_o.id*3):
                self.logger.debug(f"player {self.player_o} won vertical on column {line}")
                self.game_data["status"] = "finished-player2"
                return self.player_o.id

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == (self.player_x.id*3):
            self.logger.debug(f"player {self.player_x} won diagonally /")
            self.game_data["status"] = "finished-player1"
            return self.player_x.id
        elif diag == (self.player_o.id*3):
            self.logger.debug(f"player {self.player_o} won diagonally /")
            self.game_data["status"] = "finished-player2"
            return self.player_o.id
        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == (self.player_x.id*3):
            self.logger.debug(f"player {self.player_x} won diagonally \\")
            self.game_data["status"] = "finished-player1"
            return self.player_x.id
        elif diag == (self.player_o.id*3):
            self.logger.debug(f"player {self.player_o} won diagonally \\")
            self.game_data["status"] = "finished-player2"
            return self.player_o.id

        if any(i == 0 for row in self.board for i in row):
            return None
        self.game_data["status"] = "finished-draw"
        return self.Tie


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicTacToe(bot)) # type: ignore
