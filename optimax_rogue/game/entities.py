"""Describes the entities that are on the map. These are stored separately
from the World"""
import typing

import optimax_rogue.networking.serializer as ser

from optimax_rogue.game.modifiers import Modifier
import optimax_rogue.game.attribles as attrs
from optimax_rogue.game.items import Item

class Entity(ser.Serializable):
    """The base class for any entity

    Attributes:
        iden (int): A unique identifier for this entity
        depth (int): What layer this entity is on
        x (int): The x-position of this entity
        y (int): The y-position of this entity

        health (int): The current health for this entity
        base_max_health (int): The base maximum health for this entity
        max_health (Attrible[int]): The maximum health for this entity
        base_damage (int): the base damage for this entity
        damage (Attrible[int]): the damage for this entity
        base_armor (int): the base armor for this entity
        armor (Attrible[int]): the armor for this entity

        modifiers (list[Modifier]): the modifiers on this entity
        items (dict[int, Item]): the items this entity is carrying where the keys
            are the location
    """
    def __init__(self, iden: int, depth: int, x: int, y: int, health: int,
                 base_max_health: int, base_damage: int, base_armor: int,
                 modifiers: typing.List[Modifier], items: typing.Dict[int, Item]):
        self.iden = iden
        self.depth = depth
        self.x = x #pylint: disable=invalid-name
        self.y = y #pylint: disable=invalid-name
        self.health = health
        self.base_max_health = base_max_health
        self.max_health = attrs.MaxHealthAttrible(self)
        self.base_damage = base_damage
        self.damage = attrs.DamageAttrible(self)
        self.base_armor = base_armor
        self.armor = attrs.ArmorAttrible(self)
        self.modifiers = modifiers
        self.items = items

    def copy(self) -> 'Entity':
        """Returns a deep copy of this entity"""
        newent = type(self)(self.iden, self.depth, self.x, self.y, self.health,
                            self.base_max_health, self.base_damage, self.base_armor, None, None)

        newent.modifiers = [mod.copy(newent) for mod in self.modifiers]
        newent.items = [(key, val.copy()) for key, val in self.items.items()]
        return newent

    def on_tick(self, game_state: 'GameState') -> None:
        """Invoked every tick to update attribles"""
        self.max_health.on_tick(game_state)
        self.damage.on_tick(game_state)
        self.armor.on_tick(game_state)

    def to_prims(self):
        return {
            'iden': self.iden,
            'x': self.x,
            'y': self.y,
            'health': self.health,
            'base_max_health': self.base_max_health,
            'base_damage': self.base_damage,
            'base_armor': self.base_armor,
            'modifiers': [ser.serialize_embeddable(mod) for mod in self.modifiers],
            'items': dict((key, ser.serialize_embeddable(val)) for key, val in self.items),
        }

    @classmethod
    def from_prims(cls, prims: dict) -> 'Entity':
        cpprims = prims.copy()
        cpprims['modifiers'] = [ser.deserialize_embeddable(mod) for mod in prims['modifiers']]
        cpprims['items'] = dict((key, ser.deserialize_embeddable(val)) for key, val in prims['items'])
        return cls(**cpprims)
