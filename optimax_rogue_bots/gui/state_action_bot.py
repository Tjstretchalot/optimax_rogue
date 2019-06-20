"""Describes a bot which specifically evaluates state-action pairs and returns
some value proportional to the cumulative discounted expected reward
"""
import typing

import optimax_rogue_bots.bot as bot
import optimax_rogue.game.state as state
import optimax_rogue.logic.moves as moves

import optimax_rogue_bots.gui.packets as gpackets

class StateActionBot(bot.Bot):
    """A bot which evaluates state action pairs to decide its moves"""
    @classmethod
    def scale_style(cls) -> gpackets.SetScaleStylePacket:
        """Returns the scale style packet that the bot prefers"""
        return gpackets.SetScaleStylePacket(gpackets.ScaleStyle.TemperatureSoftArgMax, 0.02)

    @classmethod
    def pitch(cls) -> typing.Tuple[str, str]:
        """Returns the bots name and description respectively"""
        raise NotImplementedError

    @classmethod
    def supported_moves(cls) -> typing.List[moves.Move]:
        """Returns the list of the moves that the bot supports"""
        raise NotImplementedError

    def evaluate(self, game_state: state.GameState, move: moves.Move) -> float:
        """Returns someething proportional to the bots cumulative discounted
        expected reward. These values will be interpreted according to the bots
        scale style.
        """
        raise NotImplementedError
