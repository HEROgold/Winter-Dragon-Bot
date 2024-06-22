
import discord  # type: ignore
from discord import app_commands

from _types.bot import WinterDragon
from _types.cogs import GroupCog
from tools.database_tables import Game, Session, Suggestion, engine


class Games(GroupCog):
    games: list[Game]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        with Session(engine) as session:
            self.games = session.query(Game).all()


    @app_commands.command(name="list", description="Get a list of known games")
    async def slash_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(", ".join(map(str, self.games)), ephemeral=True)


    @app_commands.command(name="suggest", description="Suggest a new game to be added")
    async def slash_suggest(self, interaction: discord.Interaction, name: str) -> None:
        with Session(engine) as session:
            for suggestion in session.query(Suggestion).where(Suggestion.type == "game").all():
                if suggestion.content == name:
                    await interaction.response.send_message("That game is already in review", ephemeral=True)

            session.add(Suggestion(
                type = "game",
                is_verified = False,
                content = name,
            ))
            session.commit()
        await interaction.response.send_message(f"Added `{name}` for review", ephemeral=True)


async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(Games(bot))
