"""Describes the entire state of the game."""

import typing
import io
import optimax_rogue.networking.serializer as ser
from optimax_rogue.game.world import World
from optimax_rogue.game.entities import Entity

class GameState(ser.Serializable):
    """The entire game state of the world. If not actively updating, this instance
    completely describes everything that a new spectator needs

    Attributes:
        world (World): the world
        entities [list[Entity]]: the entities in the world
        pos_lookup (dict[(depth, x, y), Entity]): a lookup from positions to entities
    """
    def __init__(self, world: World, entities: typing.List[Entity]):
        self.world = world
        self.entities = entities
        self.pos_lookup = dict(((ent.depth, ent.x, ent.y), ent) for ent in entities)

    def on_tick(self):
        """This does not move time forward, it simply ensures all the references and attribles
        are up to date"""
        self.world.on_tick(self)
        for ent in self.entities:
            ent.on_tick(self)

    def move_entity(self, entity, newdepth, newx, newy):
        """Convenience function for moving an existing entity"""
        del self.pos_lookup[(newdepth, entity.x, entity.y)]
        entity.x = newx
        entity.y = newy
        self.pos_lookup[(newdepth, newx, newy)] = entity

    def add_entity(self, entity):
        """Convenience function for adding an entity to the world"""
        self.entities.append(entity)
        self.pos_lookup[(entity.depth, entity.x, entity.y)] = entity

    def remove_entity(self, entity):
        """Convenience function for removing an entity from the world"""
        del self.pos_lookup[(entity.depth, entity.x, entity.y)]
        self.entities.remove(entity)

    @classmethod
    def has_custom_serializer(cls) -> bool:
        return True

    def to_prims(self) -> bytes:
        arr = io.BytesIO()
        wserd = ser.serialize(self.world)
        arr.write(len(wserd).to_bytes(8, byteorder='big', signed=False))
        arr.write(wserd)

        arr.write(len(self.entities).to_bytes(4, byteorder='big', signed=False))
        for ent in self.entities:
            eserd = ser.serialize(ent)
            arr.write(len(eserd).to_bytes(4, byteorder='big', signed=False))
            arr.write(eserd)

        return arr.getvalue()

    @classmethod
    def from_prims(cls, prims: bytes) -> 'GameState':
        arr = io.BytesIO(prims)
        arr.seek(0, 0)
        wlen = int.from_bytes(arr.read(8), 'big', False)
        world = ser.deserialize(arr.read(wlen))

        nents = int.from_bytes(arr.read(4), 'big', False)
        entities = []
        for _ in range(nents):
            elen = int.from_bytes(arr.read(4), 'big', False)
            ent = ser.deserialize(arr.read(elen))
            entities.append(ent)

        return cls(world, entities)
