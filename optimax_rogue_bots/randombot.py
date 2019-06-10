"""This bot randomly moves about"""
import typing
import optimax_rogue_bots.bot as bot
from optimax_rogue.logic.moves import Move
import random

class RandomBot(bot.Bot):
    """A bot that just randomly selects a move

    Attributes:
        moves (list[Move]): the list of moves we consider
    """

    def __init__(self, entity_iden: int, moves: typing.List[Move] = None):
        super().__init__(entity_iden)
        if moves is None:
            moves = list(Move)
        self.moves = moves

    def move(self, game_state):
        return random.choice(self.moves)
