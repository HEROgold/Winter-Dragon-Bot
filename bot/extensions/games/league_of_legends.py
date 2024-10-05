from bot import WinterDragon
from bot._types.cogs import Cog


class LeagueOfLegends(Cog):
    """
    This Cog is for the League of Legends game.
    It allows users to get information about their games.
    It can watch and track (ranked) games.

    It can also track the user their:
    - rank and rank history.
    - match history.
    - champion mastery.
    - champion statistics.
    - champion leaderboard.


    Parameters
    -----------
    :param:`Cog`: :class:`_type_`
        _description_
    """



async def setup(bot: WinterDragon) -> None:
    await bot.add_cog(LeagueOfLegends(bot))
