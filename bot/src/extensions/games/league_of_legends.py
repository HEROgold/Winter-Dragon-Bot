from core.bot import WinterDragon
from core.cogs import Cog


class LeagueOfLegends(Cog):
    """League of Legends game.

    It allows users to get information about their games.
    It can watch and track (ranked) games.

    It can also track the user their:
    - rank and rank history.
    - match history.
    - champion mastery.
    - champion statistics.
    - champion leaderboard.
    """



async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(LeagueOfLegends(bot))
