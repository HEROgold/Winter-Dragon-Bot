"""Tournament strategies package."""

from winter_dragon.bot.extensions.tournaments.strategies.double_elimination import DoubleEliminationStrategy
from winter_dragon.bot.extensions.tournaments.strategies.ffa import FFAStrategy
from winter_dragon.bot.extensions.tournaments.strategies.round_robin import RoundRobinStrategy
from winter_dragon.bot.extensions.tournaments.strategies.single_elimination import SingleEliminationStrategy


strategies = [
    SingleEliminationStrategy,
    DoubleEliminationStrategy,
    RoundRobinStrategy,
    FFAStrategy,
]
