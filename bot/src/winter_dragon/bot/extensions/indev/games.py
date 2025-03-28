
import discord
from discord import app_commands
from sqlmodel import select
from winter_dragon.bot.core.bot import WinterDragon
from winter_dragon.bot.core.cogs import GroupCog
from winter_dragon.database.tables import Game, Suggestion


class Games(GroupCog):
    games: list[Game]

    def __init__(self, *args: WinterDragon, **kwargs: WinterDragon) -> None:
        super().__init__(*args, **kwargs)
        with self.session as session:
            self.games = session.exec(select(Game)).all()


    @app_commands.command(name="list", description="Get a list of known games")
    async def slash_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(", ".join(map(str, self.games)), ephemeral=True)


    @app_commands.command(name="suggest", description="Suggest a new game to be added")
    async def slash_suggest(self, interaction: discord.Interaction, name: str) -> None:
        with self.session as session:
            for suggestion in session.exec(select(Suggestion).where(Suggestion.type == "game")).all():
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
    """Entrypoint for adding cogs."""
    await bot.add_cog(Games(bot))
