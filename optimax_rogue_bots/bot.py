"""Base class for all bots"""
import optimax_rogue.game.state as state
import optimax_rogue.logic.moves as moves
class Bot:
    """Describes something which is capable of automatically selecting moves

    Attributes:
        entity_iden (int): the entity this bot controls
    """
    def __init__(self, entity_iden: int):
        self.entity_iden = entity_iden

    def move(self, game_state: state.GameState) -> moves.Move:
        """Determines the move that the bot is going to make"""
        raise NotImplementedError
