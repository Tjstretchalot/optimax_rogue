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
        is_authoritative (bool): True if this is an authoritative state (i.e., on the server)
            and False if it is not (i.e., on a client)
        tick (int): the current time / which tick we are in
        player_1_iden (int): the identifier for the entity for player 1
        player_2_iden (int): the identifier for the entity for player 2
        world (World): the world
        entities [list[Entity]]: the entities in the world
        pos_lookup (dict[(depth, x, y), Entity]): a lookup from positions to entities
        iden_lookup (dict[int, Entity]): a lookup from idens to identities
    """
    def __init__(self, is_authoritative: bool, tick: int, player_1_iden: int,
                 player_2_iden: int, world: World, entities: typing.List[Entity]):
        self.is_authoritative = is_authoritative
        self.tick = tick
        self.player_1_iden = player_1_iden
        self.player_2_iden = player_2_iden
        self.world = world
        self.entities = entities
        self.pos_lookup = dict(((ent.depth, ent.x, ent.y), ent) for ent in entities)
        self.iden_lookup = dict((ent.iden, ent) for ent in entities)

    @property
    def player_1(self) -> Entity:
        """Get the entity for player 1"""
        return self.iden_lookup[self.player_1_iden]

    @property
    def player_2(self) -> Entity:
        """Get the entity for player 2"""
        return self.iden_lookup[self.player_2_iden]

    def on_tick(self):
        """This does not move time forward, it simply ensures all the references and attribles
        are up to date"""
        self.world.on_tick(self)
        for ent in self.entities:
            ent.on_tick(self)

    def view_for(self, entity: Entity, reduce_tick: bool = False) -> 'GameState':
        """Creates a non-authoritative view appropriate for the given entity"""
        new_world = self.world.shallow_copy_with_layers(entity.depth)
        new_entities = [ent for ent in self.entities if ent.depth == entity.depth]
        new_tick = self.tick - 1 if reduce_tick else self.tick
        return GameState(False, new_tick, self.player_1_iden, self.player_2_iden, new_world, new_entities)

    def view_spec(self) -> 'GameState':
        """Creates a non-authoritative view appropriate for a spectator"""
        return GameState(False, self.tick, self.player_1_iden, self.player_2_iden, self.world, self.entities)

    def move_entity(self, entity, newdepth, newx, newy):
        """Convenience function for moving an existing entity"""
        if (entity.depth, entity.x, entity.y) not in self.pos_lookup:
            print('[gamestate] about to error on move_entity')
            for key, val in self.pos_lookup.items():
                if val == entity:
                    print(f'[gamestate] found stored location: {key}')
            print(f'[gamestate] search location: {entity.depth}, {entity.x}, {entity.y}')
        del self.pos_lookup[(entity.depth, entity.x, entity.y)]
        entity.depth = newdepth
        entity.x = newx
        entity.y = newy
        self.pos_lookup[(newdepth, newx, newy)] = entity

    def add_entity(self, entity):
        """Convenience function for adding an entity to the world"""
        self.entities.append(entity)
        self.pos_lookup[(entity.depth, entity.x, entity.y)] = entity
        self.iden_lookup[entity.iden] = entity

    def remove_entity(self, entity):
        """Convenience function for removing an entity from the world"""
        del self.pos_lookup[(entity.depth, entity.x, entity.y)]
        del self.iden_lookup[entity.iden]
        self.entities.remove(entity)

    @classmethod
    def has_custom_serializer(cls) -> bool:
        return True

    def to_prims(self) -> bytes:
        arr = io.BytesIO()
        auth_val = 1 if self.is_authoritative else 0
        arr.write(auth_val.to_bytes(1, byteorder='big', signed=False))
        arr.write(self.tick.to_bytes(4, byteorder='big', signed=False))
        arr.write(self.player_1_iden.to_bytes(4, byteorder='big', signed=False))
        arr.write(self.player_2_iden.to_bytes(4, byteorder='big', signed=False))

        wserd: bytes = self.world.to_prims()
        arr.write(len(wserd).to_bytes(8, byteorder='big', signed=False))
        arr.write(wserd)

        arr.write(len(self.entities).to_bytes(4, byteorder='big', signed=False))
        for ent in self.entities:
            eserd: bytes = ser.serialize(ent)
            arr.write(len(eserd).to_bytes(4, byteorder='big', signed=False))
            arr.write(eserd)

        return arr.getvalue()

    @classmethod
    def from_prims(cls, prims: bytes) -> 'GameState':
        arr = io.BytesIO(prims)
        arr.seek(0, 0)
        auth_val = int.from_bytes(arr.read(1), 'big', signed=False)
        tick = int.from_bytes(arr.read(4), 'big', signed=False)
        p1_iden = int.from_bytes(arr.read(4), 'big', signed=False)
        p2_iden = int.from_bytes(arr.read(4), 'big', signed=False)
        wlen = int.from_bytes(arr.read(8), 'big', signed=False)
        world = World.from_prims(arr.read(wlen))

        nents = int.from_bytes(arr.read(4), 'big', signed=False)
        entities = []
        for _ in range(nents):
            elen = int.from_bytes(arr.read(4), 'big', signed=False)
            ent = ser.deserialize(arr.read(elen))
            entities.append(ent)

        return cls(auth_val == 1, tick, p1_iden, p2_iden, world, entities)

    def __eq__(self, other):
        if not isinstance(other, GameState):
            return False
        if self.is_authoritative != other.is_authoritative:
            return False
        if self.tick != other.tick:
            return False
        if self.player_1_iden != other.player_1_iden:
            return False
        if self.player_2_iden != other.player_2_iden:
            return False
        if self.world != other.world:
            return False
        if len(self.entities) != len(other.entities):
            return False
        for ind, ent in enumerate(self.entities):
            if ent != other.entities[ind]:
                return False
        return True

    def __repr__(self) -> str:
        return (f'GameState [is_authoritative={repr(self.is_authoritative)}, '
                + f'tick={repr(self.tick)}, player_1_iden={repr(self.player_1_iden)}, '
                + f'player_2_iden={repr(self.player_2_iden)}, world={repr(self.world)}, '
                + f'entities=[' + ', '.join(repr(ent) for ent in self.entities)
                + ']]')

ser.register(GameState)
