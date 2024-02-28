from enum import Enum
from typing import Self


class Generators(Enum):
    Candy = 1
    Ferrari = 2
    Peru = 3
    Mystic = 4
    Gamboge = 5
    Chrome = 6
    Selective = 7
    Tangerine = 8
    Golden = 9
    Canary = 10
    Chartreuse = 11
    Lime = 12
    Bitter = 13
    Spring = 14
    Mango = 15
    Lawn = 16
    Chlorophyll = 17
    Harlequin = 18
    Ultramarine = 19
    Phlox = 20
    Cerulean = 21
    Fuchsia = 22
    Guppy = 23
    Crimson = 24
    Cornflower = 25


    @classmethod
    def generation_rate(cls, generator: Self) -> float:
        val = generator.value / 2 if generator.value >> 2 == 0 else generator.value >> 2
        return val / 2
