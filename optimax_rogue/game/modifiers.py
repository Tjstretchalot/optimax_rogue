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

    def to_prims(self):
        return {'damage': self.damage, 'tags': list(self.tags)}

ser.register(AttackResult)

class AttackEventArgs(ser.Serializable):
    """These are the arguments to the 'parent_attack' event. This event is invoked
    when the parent for the modifier attacks another entity

    Attributes:
        defender_iden (int): the identifier for the defender
        attack_result (AttackResult): the result of the attack
    """
    def __init__(self, defender_iden: int, attack_result: AttackResult):
        self.defender_iden = defender_iden
        self.attack_result = attack_result

    def to_prims(self):
        return {'defender_iden': self.defender_iden,
                'attack_result': ser.serialize_embeddable(self.attack_result)}

    @classmethod
    def from_prims(cls, prims) -> 'AttackEventArgs':
        return cls(prims['defender_iden'], ser.deserialize_embeddable(prims['attack_result']))

ser.register(AttackEventArgs)

class DefendEventArgs(ser.Serializable):
    """These are the arguments to the 'parent_defend' event. This event is invoked
    when the parent for the modifier is attacked by another entity. The defend
    callbacks are interweaved after the attack callbacks (i.e., it goes
    on_attack, on_defend, post_attack, post_defend)

    Attributes:
        attacker_iden (int): the identifier for the attacker
        attack_result (AttackResult): the result of the attack.
    """
    def __init__(self, attacker_iden: int, attack_result: AttackResult):
        self.attacker_iden = attacker_iden
        self.attack_result = attack_result

    def to_prims(self):
        return {'attacker_iden': self.attacker_iden,
                'attack_result': ser.serialize_embeddable(self.attack_result)}

    @classmethod
    def from_prims(cls, prims) -> 'AttackEventArgs':
        return cls(prims['attacker_iden'], ser.deserialize_embeddable(prims['attack_result']))

ser.register(DefendEventArgs)

class TickEventArgs(ser.Serializable):
    """This corresponds to the 'tick' event, which is invoked at the end of every
    timestep after moves have been resolved."""
    pass

class Modifier(ser.Serializable):
    """Describes something which is capable of modifying an entity.

    Attributes:
        parent (Entity): who this modifier is attached to
        flat_armor (int): the flat armor modifier
        flat_max_health (int): the flat max health modifier
        flat_damage (int): the flat damage modifier
        dict[str, list[ModifierEventHandler]]: the event handlers for this modifier
    """

    def __init__(self, parent: 'Entity', flat_armor: int, flat_max_health: int,
                 flat_damage: int) -> None:
        self.parent = parent
        self.flat_armor = flat_armor
        self.flat_max_health = flat_max_health
        self.flat_damage = flat_damage

    def handles(self, event_name: str) -> bool:
        """Returns True if this handler handles the specified event, False otherwise
        """
        raise NotImplementedError

    def pre_event(self, event_name: str, game_state: 'GameState', args: ser.Serializable) -> ser.Serializable:
        """Generates the state that is necessary for this event handler to
        handle the given event. This function is only invoked on the server,
        but the result is passed to the server and clients.
        """
        raise NotImplementedError

    def on_event(self, event_name: str, game_state: 'GameState',
                 args: ser.Serializable, prevals: ser.Serializable) -> None:
        """A completely deterministic function which is called while the result
        of the event can still be modified, in a specific order dependent on the
        event."""
        raise NotImplementedError

    def post_event(self, event_name: str, game_state: 'GameState',
                   args: ser.Serializable, prevals: ser.Serializable) -> None:
        """A completely deterministic function which is called after the result
        of the event has been determined, in a specific order dependent on the event
        """
        raise NotImplementedError
