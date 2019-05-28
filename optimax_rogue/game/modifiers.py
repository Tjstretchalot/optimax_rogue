"""Describes the modifier system in the game."""

import optimax_rogue.networking.serializer as ser
import typing

class AttackResult(ser.Serializable):
    """Describes the result from a particular attack. May be modified
    in the on_attack function but not the post_attack functions

    Attributes:
        damage (int): how much damage is applied to the entity
        tags (set[str]): a set of tags that are on this attack, i.e. 'blocked'
    """
    def __init__(self, damage: int, tags: typing.Set[str]):
        self.damage = damage
        self.tags = set(tags if tags is not None else [])

ser.register(AttackResult)

class Modifier(ser.Serializable):
    """Describes something which is capable of modifying an entity

    Attributes:
        parent (Entity): who this modifier is attached to
    """

    def __init__(self, parent: 'Entity') -> None:
        self.parent = parent

    def get_flat_armor(self) -> int:
        """Returns the flat change to armor this entity applies on the parent"""
        return 0

    def get_flat_max_health(self) -> int:
        """Returns the flat change to maximum health this entity applies on the parent"""
        return 0

    def get_flat_damage(self) -> int:
        """Returns the flat change to damage this entity applies on the parent"""
        return 0

    def on_parent_attacks(self, defender: 'Entity', result: AttackResult) -> None:
        """Invoked when the parent attacks another entity, defender, but before the
        attack has been resolved. May modify the attack result"""
        pass

    def post_parent_attack(self, defender: 'Entity', result: AttackResult) -> None:
        """Invoked after an attack by the parent to the given defender has been
        resolved (insofar as damage calculation)."""
        pass

    def on_parent_defends(self, attacker: 'Entity', result: AttackResult) -> None:
        """Invoked when the parent is attacked by another entity, attacker, after
        the on_parent_attacks handlers have been invoked for the attacker. May be
        used to modify the attack result"""
        pass

    def post_parent_defends(self, attacker: 'Entity', result: AttackResult) -> None:
        """Invoked when the parent is attacked by attacker, after the attackers
        post_parent_attack handlers have been invoked. May not modify the attack result"""
        pass

    def on_tick(self, game_state: 'GameState'):
        """Invokes at every tick in the game state."""
        pass
