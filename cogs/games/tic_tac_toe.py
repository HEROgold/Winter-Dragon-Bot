import json
import logging
import os
import random

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View

import config
import dragon_database
import rainbow

class TicTacToe(commands.GroupCog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger(f"winter_dragon.{self.__class__.__name__}")
        self.data = None
        self.DATABASE_NAME = self.__class__.__name__
        self.WINNING_MOVES = [
            # Left > Right
            [1,2,3],
            [4,5,6],
            [7,8,9],
            # Up > Down
            [1,4,7],
            [2,5,8],
            [3,6,9],
            # Diagonals
            [1,5,9],
            [3,5,7]
            ]
        if not config.Main.USE_DATABASE:
            self.DBLocation = f"./Database/{self.DATABASE_NAME}.json"
            self.setup_json()

    def setup_json(self) -> None:
        if not os.path.exists(self.DBLocation):
            with open(self.DBLocation, "w") as f:
                data = self.data
                json.dump(data, f)
                f.close
                self.logger.info(f"{self.DATABASE_NAME} Json Created.")
        else:
            self.logger.info(f"{self.DATABASE_NAME} Json Loaded.")

    async def get_data(self) -> dict:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            data = await db.get_data(self.DATABASE_NAME)
        else:
            with open(self.DBLocation, "r") as f:
                data = json.load(f)
        return data

    async def set_data(self, data) -> None:
        if config.Main.USE_DATABASE:
            db = dragon_database.Database()
            await db.set_data(self.DATABASE_NAME, data=data)
        else:
            with open(self.DBLocation, "w") as f:
                json.dump(data, f)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.data:
            self.data = await self.get_data()

    async def cog_unload(self) -> None:
        await self.set_data(self.data)

    async def update_view(self, view:discord.ui.View, *items) -> discord.ui.View:
        view.clear_items()
        for item in items:
            view.add_item(item)
        return view

    @app_commands.checks.cooldown(2, 60)
    @app_commands.command(
        name = "stats",
        description="view tic-tac-toe stats"
    )
    async def slash_leader_board(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = await self.get_data()
        gs_temp = None
        for game_data in self.data.values():
            status:str = game_data["status"]
            if not status.startswith("finished"):
                continue
            gs_temp = {"total":0, "abandoned":0, "wins":0, "losses":0, "draws":0}
            user_id = str(interaction.user.id)
            if status == "finished-abandoned":
                gs_temp["abandoned"] +=1
            elif status == "finished-draw":
                gs_temp["draws"] += 1
            if user_id == game_data["member1"]["id"]:
                if status == "finished-player1":
                    gs_temp["wins"] += 1
                elif status == "finished-player2":
                    gs_temp["losses"] += 1
            if user_id == game_data["member2"]["id"]:
                if status == "finished-player1":
                    gs_temp["losses"] += 1
                elif status == "finished-player2":
                    gs_temp["wins"] += 1
            gs_temp["total"] += 1

        if not gs_temp:
            await interaction.response.send_message("No gamestats to display.", ephemeral=True)
            return

        embed=discord.Embed(title="Stats", description="Your Tic Tac Toe Stats", color=random.choice(rainbow.RAINBOW))
        for name, value in gs_temp.items():
            embed.add_field(name=name, value=value, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(
        name="new",
        description="Start a tic tac toe game, which player can join"
    )
    async def slash_tic_tac_toe(self, interaction:discord.Interaction) -> None:
        if not self.data:
            self.data = await self.get_data()
        if not self.data:
            self.data = {
                "DUMMY": {
                    "status": "waiting",
                    "member1": {"id": 0, "moves": []},
                    "member2": {"id": 0, "moves": []},
                        "gamestate": {
                            "user_turn": 0,
                            "empty_moves": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                            "game_msg": {
                                "board": "`DUMMY`",
                                "turn_msg": "Game Waiting"
                                }
                        }
                    }
                }
        button1, button2 = await self.button_handler()
        view = View()
        view = await self.update_view(view, button1, button2)
        await interaction.response.send_message("Lobby created!\nJoin here to start playing!", view=view)
        resp_msg = await interaction.original_response()
        self.data[str(resp_msg.id)] = {"status":"waiting", "member1":{"id":0, "moves":[]}, "member2":{"id":0, "moves":[]}}
        await self.lobby_checker(interaction)
        await self.set_data(self.data)

# LOBBY start

    async def lobby_checker(self, interaction:discord.Interaction) -> None:
        for game_id, game_data in self.data.items():
            if game_id == "DUMMY":
                continue
            if game_data["status"] in ["waiting", "finished"]:
                continue
            member1 = game_data["member1"]
            member2 = game_data["member2"]
            if member1["id"] != 0:
                self.logger.debug(f"Member1 is ready. game_id=`{game_id}`")
            elif member2["id"] != 0:
                self.logger.debug(f"Member2 is ready. game_id=`{game_id}`")

# LOBBY end
# BOTTON start

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

# BUTTON end
# GAME start

    async def start_game(self, interaction:discord.Interaction, game_data:str) -> None:
        await interaction.edit_original_response(content="Game is starting soon!", view=None)
        game_data["status"] = "setup"
        await self.game_handler(interaction, game_data)
        # Start a match between 2 players, only allow those 2 to react.

    async def place_move(self, interaction:discord.Interaction, spot:int) -> None:
        self.logger.debug(f"{interaction.user.id} chose button {spot}")
        await interaction.response.defer()
        original_interaction = await interaction.original_response()
        # game_data = self.data[str(original_interaction.id)]
        for game_id, game_data in self.data.items():
            # self.logger.debug(f"Placing move check for: game_id=`{game_id}")

            # if interaction.user.id in [game_data["member1"]["id"], game_data["member2"]["id"]] and game_data["status"] == "running":
            if str(game_id) == str(original_interaction.id):
                break

        gamestate = game_data["gamestate"]
        user_turn = gamestate["user_turn"]
        member1 = discord.utils.get(interaction.guild.members, id=game_data["member1"]["id"])
        member2 = discord.utils.get(interaction.guild.members, id=game_data["member2"]["id"])
        player1_moves = list(game_data["member1"]["moves"])
        player2_moves = list(game_data["member2"]["moves"])
        empty:list = gamestate["empty_moves"]
        if (
            game_data["status"] == "running" and (
                spot in player1_moves and spot not in player2_moves and spot in empty or
                spot not in player1_moves and spot in player2_moves and spot in empty
                )
            ):
            self.logger.debug("Move already used!")
            return
        elif user_turn != interaction.user.id:
            self.logger.debug(f"{interaction.user.id} tried placing on {user_turn}`s turn")
            return
        elif user_turn == member1.id:
            game_data["member1"]["moves"].append(spot)
            game_data["gamestate"]["user_turn"] = member2.id
        elif user_turn == member2.id:
            game_data["member2"]["moves"].append(spot)
            game_data["gamestate"]["user_turn"] = member1.id
        else:
            return
        
        empty.remove(spot)
        await self.game_handler(interaction, game_data)
        self.logger.debug(f"Placing move check > end. empty=`{empty}`")

    async def game_handler(self, interaction:discord.Interaction, game_data:dict, view:View=View()) -> None:
        player_1 = game_data["member1"]
        player_2 = game_data["member2"]
        member1:discord.Member = discord.utils.get(interaction.guild.members, id=player_1["id"])
        # member2:discord.Member = discord.utils.get(interaction.guild.members, id=player_2["id"])
        try:
            gsam = game_data["gamestate"]
        except KeyError:
            gsam = None
        if not gsam:
            game_data["gamestate"] = {
                "user_turn":member1.id,
                "empty_moves":[1,2,3,4,5,6,7,8,9]
            }

        gamestate = game_data["gamestate"]
        user_turn = gamestate["user_turn"]

        p1_moves = game_data["member1"]["moves"]
        p2_moves = game_data["member2"]["moves"]

        can_act:discord.Member = discord.utils.get(interaction.guild.members, id=user_turn)
        if game_data["status"] == "running":
            s1 = ["x" if 1 in p1_moves else "o" if 1 in p2_moves else "_"][0]
            s2 = ["x" if 2 in p1_moves else "o" if 2 in p2_moves else "_"][0]
            s3 = ["x" if 3 in p1_moves else "o" if 3 in p2_moves else "_"][0]
            s4 = ["x" if 4 in p1_moves else "o" if 4 in p2_moves else "_"][0]
            s5 = ["x" if 5 in p1_moves else "o" if 5 in p2_moves else "_"][0]
            s6 = ["x" if 6 in p1_moves else "o" if 6 in p2_moves else "_"][0]
            s7 = ["x" if 7 in p1_moves else "o" if 7 in p2_moves else "_"][0]
            s8 = ["x" if 8 in p1_moves else "o" if 8 in p2_moves else "_"][0]
            s9 = ["x" if 9 in p1_moves else "o" if 9 in p2_moves else "_"][0]
        else:
            s1, s2, s3, s4, s5, s6, s7, s8, s9 = "_________"
            game_data["status"] = "running"

        board_as_str = f"`|  {s1}  |  {s2}  |  {s3}  |\n|_____+_____+_____|\n|  {s4}  |  {s5}  |  {s6}  |\n|_____+_____+_____|\n|  {s7}  |  {s8}  |  {s9}  |`"
        game_data["gamestate"]["game_msg"] = {
            "board":board_as_str,
            "turn_msg":f"Game Started\n{can_act.mention}'s Turn\n"
        }
        game_msg = f'{gamestate["game_msg"]["turn_msg"]}{gamestate["game_msg"]["board"]}'

        async def place_move_1(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 1)
        async def place_move_2(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 2)
        async def place_move_3(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 3)
        async def place_move_4(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 4)
        async def place_move_5(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 5)
        async def place_move_6(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 6)
        async def place_move_7(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 7)
        async def place_move_8(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 8)
        async def place_move_9(interaction:discord.Interaction) -> None:
            await self.place_move(interaction, 9)

        async def exit_func(interaction:discord.Interaction) -> None:
            status = game_data["status"]
            if status not in ["finished-draw", "finished-player2", "finished-player1"]:
                game_data["status"] = "finished-abandoned"
                end_msg = f"Abandoned Match by {interaction.user.mention}"
                self.logger.debug(f"{interaction.user.id} exited match")
            elif status == "finished-player2":
                end_msg = f"{interaction.user.mention}:  O  Won!"
                self.logger.debug(f"{interaction.user.id} won match")
            elif status == "finished-player1":
                end_msg = f"{interaction.user.mention}:  X  Won!"
                self.logger.debug(f"{interaction.user.id} won match")
            board_msg = game_data['gamestate']['game_msg']['board']
            await interaction.message.edit(content=f"Game Finished\n{board_msg}\n{end_msg}", view=None)

        if 1 in p1_moves or 1 in p2_moves:
            btn1 = Button(label="1",style=discord.ButtonStyle.gray, row=1)
            btn1.disabled = True
        else:
            btn1 = Button(label="1",style=discord.ButtonStyle.primary, row=1)
        if 2 in p1_moves or 2 in p2_moves:
            btn2 = Button(label="2",style=discord.ButtonStyle.gray, row=1)
            btn2.disabled = True
        else:
            btn2 = Button(label="2",style=discord.ButtonStyle.primary, row=1)
        if 3 in p1_moves or 3 in p2_moves:
            btn3 = Button(label="3",style=discord.ButtonStyle.gray, row=1)
            btn3.disabled = True
        else:
            btn3 = Button(label="3",style=discord.ButtonStyle.primary, row=1)
        if 4 in p1_moves or 4 in p2_moves:
            btn4 = Button(label="4",style=discord.ButtonStyle.gray, row=2)
            btn4.disabled = True
        else:
            btn4 = Button(label="4",style=discord.ButtonStyle.primary, row=2)
        if 5 in p1_moves or 5 in p2_moves:
            btn5 = Button(label="5",style=discord.ButtonStyle.gray, row=2)
            btn5.disabled = True
        else:
            btn5 = Button(label="5",style=discord.ButtonStyle.primary, row=2)
        if 6 in p1_moves or 6 in p2_moves:
            btn6 = Button(label="6",style=discord.ButtonStyle.gray, row=2)
            btn6.disabled = True
        else:
            btn6 = Button(label="6",style=discord.ButtonStyle.primary, row=2)
        if 7 in p1_moves or 7 in p2_moves:
            btn7 = Button(label="7",style=discord.ButtonStyle.gray, row=3)
            btn7.disabled = True
        else:
            btn7 = Button(label="7",style=discord.ButtonStyle.primary, row=3)
        if 8 in p1_moves or 8 in p2_moves:
            btn8 = Button(label="8",style=discord.ButtonStyle.gray, row=3)
            btn8.disabled = True
        else:
            btn8 = Button(label="8",style=discord.ButtonStyle.primary, row=3)
        if 9 in p1_moves or 9 in p2_moves:
            btn9 = Button(label="9",style=discord.ButtonStyle.gray, row=3)
            btn9.disabled = True
        else:
            btn9 = Button(label="9",style=discord.ButtonStyle.primary, row=3)
        exit_btn = Button(label="Exit", style=discord.ButtonStyle.danger, row=4)

        btn1.callback = place_move_1
        btn2.callback = place_move_2
        btn3.callback = place_move_3
        btn4.callback = place_move_4
        btn5.callback = place_move_5
        btn6.callback = place_move_6
        btn7.callback = place_move_7
        btn8.callback = place_move_8
        btn9.callback = place_move_9
        exit_btn.callback = exit_func

        view.clear_items()
        for i in [btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, exit_btn]:
            view.add_item(i)

        await interaction.edit_original_response(content=game_msg, view=view)
        playermoves_1:list = player_1["moves"]
        playermoves_2:list = player_2["moves"]
        playermoves_1.sort()
        playermoves_2.sort()

        if await self.win_checker(playermoves_1) == True :
            game_data["status"] = "finished-player1"
            await exit_func(interaction)
        elif await self.win_checker(playermoves_2) == True:
            game_data["status"] = "finished-player2"
            await exit_func(interaction)
        elif gamestate["empty_moves"] == []:
            game_data["status"] = "finished-draw"

        # self.logger.debug(f"GameUpdate: game_data=`{game_data}")
        await self.set_data(self.data)

    async def win_checker(self, playermoves:list) -> bool:
        for i in range(len(playermoves)):
            self.logger.debug(f"win_check: i=`{i}` moves=`{playermoves[i:i+3]}` return=`{playermoves in self.WINNING_MOVES}`")
            if playermoves[i:i+3] in self.WINNING_MOVES:
                return True
        return False

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicTacToe(bot))
