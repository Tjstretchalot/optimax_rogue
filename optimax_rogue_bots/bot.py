"""Base class for all bots"""
import optimax_rogue.game.state as state
import optimax_rogue.logic.moves as moves
from optimax_rogue.logic.updater import UpdateResult

class Bot:
    """Describes something which is capable of automatically selecting moves

    Attributes:
        entity_iden (int): the entity this bot controls
    """
    def __init__(self, entity_iden: int):
        self.entity_iden = entity_iden

    def think(self, max_time: float) -> None:
        """Called when the bot has some time to kill, perhaps because we have some target
        tickrate and we are determining moves faster than that, or because we are waiting
        on other player moves"""
        pass

    def move(self, game_state: state.GameState) -> moves.Move:
        """Determines the move that the bot is going to make"""
        raise NotImplementedError

    def on_move(self, game_state: state.GameState, move: moves.Move) -> None:
        """Invoked when the bot has made the specified move in the specified
        game state. This could differ from the result of move(), which is the
        bots suggestion for a move.
        """
        pass

    def finished(self, game_state: state.GameState, result: UpdateResult) -> None:
        """Invoked when the game ends"""
        pass
