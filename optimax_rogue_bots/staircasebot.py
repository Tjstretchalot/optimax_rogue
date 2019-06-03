"""This bot just rushes as quickly as possible to the staircase"""

from optimax_rogue_bots.bot import Bot
import optimax_rogue.game.state as state
import optimax_rogue.logic.moves as moves

class StaircaseBot(Bot):
    """Rushes to the staircase"""
    def move(self, game_state: state.GameState):
        me = game_state.iden_lookup[self.entity_iden]
        stx, sty = game_state.world.dungeons[me.depth].staircase()

        deltax = stx - me.x
        deltay = sty - me.y
        if abs(deltax) > abs(deltay):
            if deltax > 0:
                return moves.Move.Right
            return moves.Move.Left
        if deltay > 0:
            return moves.Move.Down
        return moves.Move.Up