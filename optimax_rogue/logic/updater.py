"""This module is capable of moving the game state forward in time"""
import typing
from optimax_rogue.game.state import GameState
from optimax_rogue.game.entities import Entity
from optimax_rogue.game.modifiers import Modifier
from optimax_rogue.logic.moves import Move
import optimax_rogue.logic.updates as updates

class Updater:
    """This class handles moving time forward

    Attributes:
        current_update_order (int): the order for the next game state update
    """
    def __init__(self):
        self.current_update_order = 0

    def get_incr_upd_order(self):
        """Gets and increments (as if in that order) the current update order"""
        self.current_update_order += 1
        return self.current_update_order - 1

    def update(self, game_state: GameState, player1_move: Move,
               player2_move: Move) -> typing.List[updates.GameStateUpdate]:
        """Moves the game state forward in time, returning a list of updates
        that must be invoked on other clients to replicate this update.
        """
        pass
