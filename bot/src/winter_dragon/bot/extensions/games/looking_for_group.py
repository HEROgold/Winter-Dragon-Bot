import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.config import config
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.bot.extensions.games.games import Games
from winter_dragon.database.tables import Games as GamesDB
from winter_dragon.database.tables import LookingForGroup


@app_commands.guilds(config.getint("Main", "support_guild_id"))
class Lfg(GroupCog):
    slash_suggest = Games.slash_suggest


    def __init__(self, *args: WinterDragon, **kwargs: WinterDragon) -> None:
        super().__init__(*args, **kwargs)

        with self.session as session:
            self.games = [i.name for i in session.exec(select(GamesDB)).all()]

    # TODO: add Database table, matching user id and category, every time someone adds, check matches.
    @app_commands.command(name="join", description="Join a search queue for finding people for the same game")
    async def slash_lfg_join(self, interaction: discord.Interaction, game: str) -> None:
        with self.session as session:
            game_db = session.exec(select(GamesDB).where(GamesDB.name == game)).first()
            if game_db is None:
                await interaction.response.send_message("This game is not supported", ephemeral=True)
                return
            total = session.exec(select(LookingForGroup).where(LookingForGroup.game_name == game)).all()
            session.add(LookingForGroup(
                user_id = interaction.user.id,
                game_name = game_db.name,
            ))
            session.commit()
        c_mention = self.get_command_mention(self.slash_lfg_leave)
        msg = f"Adding you to the search queue for {game}, currently there are {len(total)} in the same queue. Use {c_mention} to leave all queues."  # noqa: E501
        await interaction.response.send_message(msg, ephemeral=True)


    @app_commands.command(name="leave", description="leave all joined search queue")
    async def slash_lfg_leave(self, interaction: discord.Interaction) -> None:
        with self.session as session:
            lfg = session.exec(select(LookingForGroup).where(LookingForGroup.user_id == interaction.user.id)).all()
            for i in lfg:
                session.delete(i)
            session.commit()
        c_mention = await self.get_command_mention(self.slash_lfg_join)
        await interaction.response.send_message(
            f"Removed you from all lfg queues, use {c_mention} to join one again.",
            ephemeral=True,
        )


    @slash_lfg_join.autocomplete("game")
    async def autocomplete_game(
        self,
        _interaction:
        discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=i, value=i)
            for i in self.games
            if current.lower() in i.lower()
        ] or [
            app_commands.Choice(name=i, value=i)
            for i in self.games
        ]


    async def search_match(self, interaction: discord.Interaction, _game: str) -> None:
        with self.session as session:
            user_games = session.exec(select(LookingForGroup).where(LookingForGroup.user_id == interaction.user.id)).all()
            for user_game in user_games:
                lfg_game = session.exec(select(LookingForGroup).where(LookingForGroup.game_name == user_game.game_name)).all()
                self.logger.debug(f"{user_game=}, {lfg_game=}")


async def setup(bot: WinterDragon) -> None:
    """Entrypoint for adding cogs."""
    await bot.add_cog(Lfg(bot))
