"""This module is capable of moving the game state forward in time"""
import typing
import random
import enum
from dataclasses import dataclass
from optimax_rogue.game.state import GameState
from optimax_rogue.game.entities import Entity
from optimax_rogue.game.modifiers import Modifier
from optimax_rogue.logic.moves import Move
import optimax_rogue.logic.updates as updates

class UpdateResult(enum.IntEnum):
    """The result from updater"""
    InProgress = 1
    Player1Win = 2
    Player2Win = 3
    Tie = 4

@dataclass
class UpdatingEntity:
    """An wrapper around an entity that is created during the update

    Attributes:
        entity (Entity): the entity before the tick
        move (Move): the move the entity made
    """

    entity: Entity
    move: Move

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
               player2_move: Move
               ) -> typing.Tuple[UpdateResult, typing.List[updates.GameStateUpdate]]:
        """Moves the game state forward in time, returning a list of updates
        that must be invoked on other clients to replicate this update.

        Returns False,
        """
        result = []

        player1 = game_state.iden_lookup[game_state.player_1_iden]
        player2 = game_state.iden_lookup[game_state.player_2_iden]

        updents = []
        updents.append(UpdatingEntity(
            entity=player1,
            move=player1_move
        ))

        updents.append(UpdatingEntity(
            entity=player2,
            move=player2_move
        ))

        random.shuffle(updents)

        player_idens = (game_state.player_1_iden, game_state.player_2_iden)
        npcs = []
        for ent in game_state.entities:
            if ent.iden in player_idens:
                continue
            npc_move: Move = self.decide_npc_move(game_state, ent, result)
            npcs.append(UpdatingEntity(
                entity=ent,
                move=npc_move
            ))
        random.shuffle(npcs)
        updents.extend(npcs)

        for ind, updent in enumerate(updents):
            self.handle_move(game_state, ind, updent, updents, result)

        if player1.health <= 0:
            return (UpdateResult.Tie if player2.health <= 0 else UpdateResult.Player2Win), result
        if player2.health <= 0:
            return UpdateResult.Player1Win
        return UpdateResult.InProgress


    def decide_npc_move(self, game_state: GameState, ent: Entity, # pylint: disable=unused-argument
                        result: typing.List[updates.GameStateUpdate]) -> Move: # pylint: disable=unused-argument
        """Determines the move that the given npc will make

        Args:
            game_state (GameState): the state of the game
            ent (Entity): the entity
            result (typing.List[updates.GameStateUpdate]): the list of client-side updates
                required for synchronization in order

        Returns:
            Move: the move the npc should make
        """
        return Move.Stay

    def handle_move(self, game_state: GameState, ind: int, ent: UpdatingEntity,
                    all_ents: typing.List[UpdatingEntity],
                    result: typing.List[updates.GameStateUpdate]) -> None:
        """This is invoked on each entity in a semi-random order (players first
        then non-players) once all moves are known.

        Arguments:
            game_state (GameState): the state of the game
            ind (int): the index of the entity being updated in all_ents - also doubles as the initiative
            for this entity
            ent (UpdatingEntity): the entity to update (all_ents[ind])
            all_ents (list[UpdatingEntity]): the ordered list of entities that are being updated
            result (list[GameStateUpdate]): the list of updates that clients need to do to
                mirror this update
        """
        pass
