"""Describes and applies updates to game states"""
import typing

import optimax_rogue.networking.serializer as ser
import optimax_rogue.game.world as world
from optimax_rogue.game.state import GameState
from optimax_rogue.game.entities import Entity
from optimax_rogue.game.modifiers import (
    Modifier, AttackEventArgs, DefendEventArgs, AttackResult, CombatFlag)


class GameStateUpdate(ser.Serializable):
    """The interface for game state updates

    Attributes:
        order (int): this number is unique to each update and identifies when it should
            be applied. GameStateUpdates should be applied in ascending order
    """

    def __init__(self, order: int) -> None:
        self.order = order

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        """Returns if this update is relevant to the given depth"""
        raise NotImplementedError

    def apply(self, game_state: GameState) -> None:
        """Applies this update to the given game state"""
        raise NotImplementedError

class EntityEventUpdate(GameStateUpdate):
    """This update corresponds with an event occuring to a specific entity. This may have
    many implications on the world based on the modifiers for the entity"""

    def __init__(self, order: int, entity_iden: int, event_name: str,
                 args: ser.Serializable,
                 prevals: typing.Tuple[ser.Serializable]) -> None:
        super().__init__(order)
        self.entity_iden = entity_iden
        self.event_name = event_name
        self.args = args
        self.prevals = prevals

    def to_prims(self):
        return {'order': self.order, 'entity_iden': self.entity_iden,
                'event_name': self.event_name,
                'args': ser.serialize_embeddable(self.args),
                'prevals': tuple(ser.serialize_embeddable(prev) for prev in self.prevals)}

    @classmethod
    def from_prims(cls, prims):
        return cls(
            prims['order'], prims['entity_iden'], prims['event_name'],
            ser.deserialize_embeddable(prims['args']),
            tuple(ser.deserialize_embeddable(prev) for prev in prims['prevals'])
        )

    def apply(self, game_state: GameState):
        """Invokes this event on the modifiers of the entity"""
        ent: Entity = game_state.iden_lookup[self.entity_iden]
        for ind, mod in enumerate(ent.modifiers):
            mod.on_event(self.event_name, game_state, self.args, self.prevals[ind])
        for ind, mod in enumerate(ent.modifiers):
            mod.post_event(self.event_name, game_state, self.args, self.prevals[ind])

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return game_state.iden_lookup[self.entity_iden].depth == depth

ser.register(EntityEventUpdate)

class EntityCombatUpdate(GameStateUpdate):
    """This update corresponds with combat between two entities on the world, which is
    a special case of two entity event updates because the parent_attack and parent_defend
    events are interleaved

    Attributes:
        attacker_iden (int): the id for the attacking entity
        defender_iden (int): the id for the defending entity
        og_damage (int): the original damage for the attack
        tags (set[CombatFlag]): the original flags for the attack
        attack_prevals (tuple[Serializable]): the synchronization arguments / random component
            for parent_attack for each modifier on the attacking ent
        defend_prevals (tuple[Serializable]): the synchronization arguments / random component
            for parent_defend for each modifier on the defending ent
    """
    def __init__(self, order: int, attacker_iden: int, defender_iden: int,
                 og_damage: int, tags: typing.Set[CombatFlag],
                 attack_prevals: typing.Tuple[ser.Serializable],
                 defend_prevals: typing.Tuple[ser.Serializable]):
        super().__init__(order)
        self.attacker_iden = attacker_iden
        self.defender_iden = defender_iden
        self.og_damage = og_damage
        self.tags = tags
        self.attack_prevals = attack_prevals
        self.defend_prevals = defend_prevals

    def to_prims(self):
        return {
            'order': self.order,
            'attacker_iden': self.attacker_iden, 'defender_iden': self.defender_iden,
            'og_damage': self.og_damage,
            'tags': tuple(self.tags),
            'attack_prevals': tuple(ser.serialize_embeddable(prev) for prev in self.attack_prevals),
            'defend_prevals': tuple(ser.serialize_embeddable(prev) for prev in self.defend_prevals),
        }

    @classmethod
    def from_prims(cls, prims) -> 'EntityCombatUpdate':
        return cls(
            prims['order'],
            prims['attacker_iden'], prims['defender_iden'], prims['og_damage'], set(prims['tags']),
            tuple(ser.deserialize_embeddable(prev) for prev in prims['attack_prevals']),
            tuple(ser.deserialize_embeddable(prev) for prev in prims['defend_prevals']),
        )

    def apply(self, game_state: GameState) -> None:
        attent: Entity = game_state.iden_lookup[self.attacker_iden]
        defent: Entity = game_state.iden_lookup[self.defender_iden]
        ares = AttackResult(self.og_damage, self.tags.copy())
        attack_args = AttackEventArgs(self.defender_iden, ares)
        defend_args = DefendEventArgs(self.attacker_iden, ares)
        for ind, mod in enumerate(attent.modifiers):
            mod.on_event('parent_attack', game_state, attack_args, self.attack_prevals[ind])
        for ind, mod in enumerate(defent.modifiers):
            mod.on_event('parent_defend', game_state, defend_args, self.defend_prevals[ind])
        for ind, mod in enumerate(attent.modifiers):
            mod.post_event('parent_attack', game_state, attack_args, self.attack_prevals[ind])
        for ind, mod in enumerate(defent.modifiers):
            mod.post_event('parent_defend', game_state, defend_args, self.defend_prevals[ind])

        if ares.damage > 0:
            defent.health -= ares.damage

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return (game_state.iden_lookup[self.attacker_iden].depth == depth
                or game_state.iden_lookup[self.defender_iden].depth == depth)

class EntitySpawnUpdate(GameStateUpdate):
    """This update corresponds with an entity spawning on the world

    Attributes:
        entity (Entity): the entity which was spawned
    """

    def __init__(self, order: int, entity: Entity) -> None:
        super().__init__(order)
        self.entity = entity

    def to_prims(self) -> typing.Any:
        return {'order': self.order, 'entity': ser.serialize_embeddable(self.entity)}

    @classmethod
    def from_prims(cls, prims):
        return cls(prims['order'], ser.deserialize_embeddable(prims['entity']))

    def apply(self, game_state: GameState) -> None:
        game_state.add_entity(self.entity)

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return self.entity.depth == depth

ser.register(EntitySpawnUpdate)

class EntityDeathUpdate(GameStateUpdate):
    """This update corresponds with an entity dying on the world

    Attributes:
        entity_iden (int): the identifier for the entity that died
    """

    def __init__(self, order: int, entity_iden: int):
        super().__init__(order)
        self.entity_iden = entity_iden

    def apply(self, game_state: GameState) -> None:
        game_state.remove_entity(game_state.iden_lookup[self.entity_iden])

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return game_state.iden_lookup[self.entity_iden].depth == depth

ser.register(EntityDeathUpdate)

class EntityPositionUpdate(GameStateUpdate):
    """This update corresponds with an entity moving on the world

    Attributes:
        entity_iden (int): the identifier for the entity which moved
        depth (int): the new depth for the entity
        depth_changed (bool): flag if the depth changed for the entity
        posx (int): the new x-coordinate for the entity
        posy (int): the new y-coordinate for the entity
    """

    def __init__(self, order: int, entity_iden: int, depth: int,
                 depth_changed: bool, posx: int, posy: int) -> None:
        super().__init__(order)
        self.entity_iden = entity_iden
        self.depth = depth
        self.depth_changed = depth_changed
        self.posx = posx
        self.posy = posy

    def apply(self, game_state: GameState) -> None:
        entity = game_state.iden_lookup[self.entity_iden]
        entity.depth = self.depth
        entity.x = self.posx
        entity.y = self.posy

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return depth in (game_state.iden_lookup[self.entity_iden].depth, self.depth)

ser.register(EntityPositionUpdate)

class EntityHealthUpdate(GameStateUpdate):
    """This update corresponds with an entity being hurt or healed

    Attributes:
        entity_iden (int): the identifier for the entity whose health changed
        source_iden (int): the identifier for the entity who caused this
        amount (int): the change in health
        tags (set[str]): additional tags associated with this update
    """

    def __init__(self, order: int, entity_iden: int, source_iden: int, amount: int,
                 tags: typing.Set[str]):
        super().__init__(order)
        self.entity_iden = entity_iden
        self.source_iden = source_iden
        self.amount = amount
        self.tags = frozenset(tags)

    def to_prims(self):
        return {'order': self.order, 'entity_iden': self.entity_iden,
                'source_iden': self.source_iden, 'amount': self.amount,
                'tags': tuple(self.tags)}

    def apply(self, game_state: GameState):
        game_state.iden_lookup[self.entity_iden].health += self.amount

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return depth in (game_state.iden_lookup[self.entity_iden].depth,
                         game_state.iden_lookup[self.source_iden].depth)

ser.register(EntityHealthUpdate)

class EntityModifierAdded(GameStateUpdate):
    """This update corresponds with an entity gaining a modifier

    Attributes:
        entity_iden (int): the identifier for the entity who gained a modifier
        modifier (Modifier): the modifier which was added
    """

    def __init__(self, order: int, entity_iden: int, modifier: Modifier):
        super().__init__(order)
        self.entity_iden = entity_iden
        self.modifier = modifier

    def to_prims(self):
        return {'order': self.order, 'entity_iden': self.entity_iden,
                'modifier': ser.serialize_embeddable(self.modifier)}

    @classmethod
    def from_prims(cls, prims):
        return cls(prims['order'], prims['entity_iden'],
                   ser.deserialize_embeddable(prims['modifier']))

    def apply(self, game_state: GameState) -> None:
        ent: Entity = game_state.iden_lookup[self.entity_iden]
        ent.modifiers.append(self.modifier)

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return depth in (game_state.iden_lookup[self.entity_iden].depth,)


ser.register(EntityModifierAdded)

class EntityModifierRemoved(GameStateUpdate):
    """This update corresponds to an entity losing a modifier

    Attributes:
        entity_iden (int): the identifier for the entity
        modifier_index (int): the index in the entities modifier list that was removed
    """
    def __init__(self, order: int, entity_iden: int, modifier_index: int):
        super().__init__(order)
        self.entity_iden = entity_iden
        self.modifier_index = modifier_index

    def apply(self, game_state: GameState) -> None:
        ent: Entity = game_state.iden_lookup[self.entity_iden]
        ent.modifiers.pop(self.modifier_index)

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return depth in (game_state.iden_lookup[self.entity_iden].depth,)

ser.register(EntityModifierRemoved)

class DungeonCreatedUpdate(GameStateUpdate):
    """Called when a dungeon is created

    Attributes:
        depth (int): the depth of the dungeon
        dungeon (Dungeon): the actual dungeon
    """
    def __init__(self, order: int, depth: int, dungeon: world.Dungeon) -> None:
        super().__init__(order)
        self.depth = depth
        self.dungeon = dungeon

    def apply(self, game_state: GameState) -> None:
        game_state.world.set_at_depth(self.depth, self.dungeon)

    def relevant_for(self, game_state: GameState, depth: int) -> bool:
        return depth == self.depth

    def to_prims(self):
        return {'order': self.order, 'depth': self.depth,
                'dungeon': ser.serialize_embeddable(self.dungeon)}

    @classmethod
    def from_prims(cls, prims):
        return cls(prims['order'], prims['depth'],
                   ser.deserialize_embeddable(prims['dungeon']))

ser.register(DungeonCreatedUpdate)