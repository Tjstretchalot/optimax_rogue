"""This bot randomly moves about"""
import optimax_rogue_bots.bot as bot
import optimax_rogue.logic.moves as moves
import random

class RandomBot(bot.Bot):
    """A bot that just randomly selects a move"""

    def move(self, game_state):
        return random.choice(list(moves.Move))
