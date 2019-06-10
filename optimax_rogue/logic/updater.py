"""This module is capable of moving the game state forward in time"""
import typing
import random
import enum
from optimax_rogue.game.state import GameState
from optimax_rogue.game.entities import Entity
from optimax_rogue.game.modifiers import (
    CombatFlag, AttackEventArgs, DefendEventArgs, AttackResult)
from optimax_rogue.game.world import Tile, Dungeon
from optimax_rogue.logic.moves import Move
from optimax_rogue.logic.worldgen import DungeonGenerator
import optimax_rogue.logic.updates as updates

import numpy as np

class UpdateResult(enum.IntEnum):
    """The result from updater"""
    InProgress = 1
    Player1Win = 2
    Player2Win = 3
    Tie = 4

class RealMove(enum.IntEnum):
    """The real move that an entity performed"""
    Rest = 1 # Stay, no combat
    Block = 2 # Stay, combat
    AttackBlocked = 3 # Move into a stay
    AttackFlee = 4 # Move into a retreating entity
    AttackAmbush = 5 # Move into the new spot for an entity
    AttackParry = 6 # Move into an entity which also moved into you
    Move = 7 # a normal movement that was unhindered
    Descend = 8 # a movement into a staircase that caused the entity to descend

class UpdatingEntity:
    """An wrapper around an entity that is created during the update

    Attributes:
        entity (Entity): the entity before the tick
        move (Move): the move the entity made
        real_move (RealMove): the real move that the entity made
    """
    def __init__(self, entity: Entity, move: Move, real_move: RealMove):
        self.entity = entity
        self.move = move
        self.real_move = real_move

class DungeonDespawningStrategy(enum.IntEnum):
    """The potential strategies that the updater uses for despawning dungeons."""
    Unreachable = 1 # despawn unreachable dungeons (i.e. above the highest player)
    Unused = 2 # despawn any dungeon without a player on it and regenerate if necessary

class Updater:
    """This class handles moving time forward

    Attributes:
        current_update_order (int): the order for the next game state update
        dgen (DungeonGenerator): the thing that spawns dungeons!

        despawn_strat (DungeonDespawningStrategy): the technique used for despawning
            dungeons
    """
    def __init__(self, dgen: DungeonGenerator, despawn_strat: DungeonDespawningStrategy):
        self.current_update_order = 0
        self.dgen = dgen
        self.despawn_strat = despawn_strat

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

        player1: Entity = game_state.iden_lookup[game_state.player_1_iden]
        player2: Entity = game_state.iden_lookup[game_state.player_2_iden]

        # check for bad player moves
        newp1x, newp1y = calculate_pos(player1.x, player1.y, player1_move)
        dung: Dungeon = game_state.world.get_at_depth(player1.depth)
        if dung.is_blocked(newp1x, newp1y):
            player1_move = Move.Stay

        newp2x, newp2y = calculate_pos(player2.x, player2.y, player2_move)
        dung: Dungeon = game_state.world.get_at_depth(player2.depth)
        if dung.is_blocked(newp2x, newp2y):
            player2_move = Move.Stay

        # set up initial moves
        updents = []
        updents.append(UpdatingEntity(
            entity=player1,
            move=player1_move,
            real_move=None
        ))

        updents.append(UpdatingEntity(
            entity=player2,
            move=player2_move,
            real_move=None
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
                move=npc_move,
                real_move=None
            ))
        random.shuffle(npcs)
        updents.extend(npcs)

        eiden_to_ind = dict((ent.entity.iden, ind) for ind, ent in enumerate(updents))

        # handle moves
        for ind, updent in enumerate(updents):
            self.handle_move(game_state, ind, updent, updents, eiden_to_ind, result)

        # handle deaths
        ind = len(game_state.entities) - 1
        while ind >= 0:
            ent: Entity = game_state.entities[ind]
            if ent.health <= 0 and ent.iden not in (game_state.player_1_iden, game_state.player_2_iden):
                    result.append(updates.EntityDeathUpdate(
                        self.get_incr_upd_order(), ent.iden
                    ))
                    game_state.remove_entity(ent)
            ind -= 1

        # increment time
        game_state.tick += 1

        # handle player deaths
        if player1.health <= 0:
            print('[updater] player 1 died')
            return (UpdateResult.Tie if player2.health <= 0 else UpdateResult.Player2Win), result
        if player2.health <= 0:
            print('[updater] player 2 died')
            return UpdateResult.Player1Win, result

        return UpdateResult.InProgress, result


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
                    all_ents: typing.List[UpdatingEntity], eiden_to_ind: typing.Dict[int, int],
                    result: typing.List[updates.GameStateUpdate]) -> None:
        """This is invoked on each entity in a semi-random order (players first
        then non-players) once all moves are known.

        Arguments:
            game_state (GameState): the state of the game
            ind (int): the index of the entity being updated in all_ents - also doubles as the
                initiative for each entity (lower is better)
            for this entity
            ent (UpdatingEntity): the entity to update (all_ents[ind])
            all_ents (list[UpdatingEntity]): the ordered list of entities that are being updated
            result (list[GameStateUpdate]): the list of updates that clients need to do to
                mirror this update
        """
        if ent.move == Move.Stay:
            if ent.real_move is None:
                ent.real_move = RealMove.Rest
            return

        newx, newy = calculate_pos(ent.entity.x, ent.entity.y, ent.move)
        if (ent.entity.depth, newx, newy) not in game_state.pos_lookup:
            dung: Dungeon = game_state.world.get_at_depth(ent.entity.depth)

            # did we descend?
            if dung.tiles[newx, newy] == Tile.StaircaseDown:
                self.handle_descend(game_state, ent, result)
                return

            # move successful!
            result.append(updates.EntityPositionUpdate(
                self.get_incr_upd_order(), ent.entity.iden, ent.entity.depth, False, newx, newy
            ))
            game_state.move_entity(ent.entity, ent.entity.depth, newx, newy)
            ent.real_move = RealMove.Move
            return

        at_pos = game_state.pos_lookup[ent.entity.depth, newx, newy]
        at_pos_ind = eiden_to_ind[at_pos.iden]
        at_pos_upde = all_ents[at_pos_ind]

        if at_pos_upde.move == Move.Stay:
            # we were blocked (very bad for us)
            self.handle_combat(game_state, ent.entity, at_pos, {CombatFlag.Block}, result)
            at_pos_upde.real_move = RealMove.Block
            ent.real_move = RealMove.AttackBlocked
            return

        at_pos_newx, at_pos_newy = calculate_pos(at_pos.x, at_pos.y, at_pos_upde.move)
        if (at_pos_newx, at_pos_newy) == (newx, newy):
            # we were parried (bad for us)
            self.handle_combat(game_state, ent.entity, at_pos, {CombatFlag.Parry}, result)
            ent.real_move = RealMove.AttackParry
            return
        if at_pos_ind < ind:
            # we both moved to the same spot and they had higher initiative (good for us)
            self.handle_combat(game_state, ent.entity, at_pos, {CombatFlag.Ambush}, result)
            ent.real_move = RealMove.AttackAmbush
            return
        # they fled from us but we had higher initiative (good for us)
        self.handle_combat(game_state, ent.entity, at_pos, {CombatFlag.Flee}, result)
        at_pos_upde.real_move = RealMove.Block
        ent.real_move = RealMove.AttackBlocked

    def should_despawn(self, game_state: GameState, depth: int):
        """Determines if we should despawn the dungeon at the given depth in
        the GameState. Does not check if the specified dungeon actually exists.
        Chosen according to the despawn strategy.
        """
        play1_depth = game_state.player_1.depth
        play2_depth = game_state.player_2.depth

        if self.despawn_strat == DungeonDespawningStrategy.Unreachable:
            return play1_depth > depth and play2_depth > depth
        elif self.despawn_strat == DungeonDespawningStrategy.Unused:
            return depth not in (play1_depth, play2_depth)
        raise ValueError(f'Unknown despawn strat {self.despawn_strat} (type={type(self.despawn_strat)})')

    def handle_descend(self, game_state: GameState, ent: UpdatingEntity,
                       result: typing.List[updates.GameStateUpdate]) -> None:
        """Handles when an entity descends by going through a staircase - this will
        kill npcs"""
        if (game_state.player_1_iden != ent.entity.iden
                and game_state.player_2_iden != ent.entity.iden):
            result.append(updates.EntityDeathUpdate(
                self.get_incr_upd_order(), ent.entity.iden
            ))
            game_state.remove_entity(ent.entity)
            ent.real_move = RealMove.Descend
            return

        old_depth = ent.entity.depth
        new_depth = old_depth + 1
        if new_depth not in game_state.world.dungeons:
            # got to spawn the dungeon!
            dungeon = self.dgen.spawn_dungeon(new_depth)
            game_state.world.set_at_depth(new_depth, dungeon)
            result.append(updates.DungeonCreatedUpdate(
                self.get_incr_upd_order(), new_depth, dungeon
            ))

        dung: Dungeon = game_state.world.get_at_depth(new_depth)
        spawn_x, spawn_y = dung.get_random_unblocked()
        while (new_depth, spawn_x, spawn_y) in game_state.pos_lookup:
            spawn_x, spawn_y = dung.get_random_unblocked()

        result.append(updates.EntityPositionUpdate(
            self.get_incr_upd_order(), ent.entity.iden,
            new_depth, True, spawn_x, spawn_y
        ))

        game_state.move_entity(ent.entity, new_depth, spawn_x, spawn_y)
        ent.real_move = RealMove.Descend

        if self.should_despawn(game_state, old_depth):
            game_state.world.del_at_depth(old_depth)

    def handle_combat(self, game_state: GameState, attacker: Entity, defender: Entity,
                      tags: typing.Set[CombatFlag], result: typing.List[updates.GameStateUpdate]):
        """Invoked when the given at

        Args:
            game_state (GameState): the state of the game
            attacker (Entity): the entity which is attacking
            defender (Entity): the entity which is defending
            tags (set[CombatFlag]): the combat flags
            result (list[GameStateUpdate]): where the updates the clients must be sent to
                replicate this update are stored
        """
        attack_prevals = []
        defend_prevals = []

        og_dmg = attacker.damage.value - attacker.armor.value
        ares = AttackResult(og_dmg, tags.copy())
        attack_args = AttackEventArgs(defender.iden, ares)
        defend_args = DefendEventArgs(attacker.iden, ares)

        for attmod in attacker.modifiers:
            attack_prevals.append(attmod.pre_event('parent_attack', game_state, attack_args))
        for defmod in defender.modifiers:
            defend_prevals.append(defmod.pre_event('parent_defend', game_state, defend_args))
        for ind, attmod in enumerate(attacker.modifiers):
            attmod.on_event('parent_attack', game_state, attack_args, attack_prevals[ind])
        for ind, defmod in enumerate(defender.modifiers):
            defmod.on_event('parent_defend', game_state, defend_args, defend_prevals[ind])
        for ind, attmod in enumerate(attacker.modifiers):
            attmod.post_event('parent_attack', game_state, attack_args, attack_prevals[ind])
        for ind, defmod in enumerate(defender.modifiers):
            defmod.post_event('parent_defend', game_state, defend_args, defend_prevals[ind])

        if ares.damage > 0:
            defender.health -= ares.damage
            print(f'[updater] player {defender.iden} at {defender.x}, {defender.y} took {ares.damage} from {attacker.iden}  at {attacker.x}, {attacker.y} (new health: {defender.health}) (tags: {tags})')

        result.append(updates.EntityCombatUpdate(
            self.get_incr_upd_order(), attacker.iden, defender.iden,
            og_dmg, tags.copy(), attack_prevals, defend_prevals
        ))

def calculate_pos(x: int, y: int, move: Move) -> typing.Tuple[int, int]:
    """Calculates the new position for an entity at (x, y) taking the specified
    move"""
    if move == Move.Up:
        return x, y - 1
    elif move == Move.Down:
        return x, y + 1
    elif move == Move.Right:
        return x + 1, y
    elif move == Move.Left:
        return x - 1, y
    return x, y
