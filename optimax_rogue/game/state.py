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
        player_1_iden (int): the identifier for the entity for player 1
        player_2_iden (int): the identifier for the entity for player 2
        world (World): the world
        entities [list[Entity]]: the entities in the world
        pos_lookup (dict[(depth, x, y), Entity]): a lookup from positions to entities
        iden_lookup (dict[int, Entity]): a lookup from idens to identities
    """
    def __init__(self, is_authoritative: bool, player_1_iden: int, player_2_iden: int,
                 world: World, entities: typing.List[Entity]):
        self.is_authoritative = is_authoritative
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

    def view_for(self, entity: Entity) -> 'GameState':
        """Creates a non-authoritative view appropriate for the given entity"""
        new_world = self.world.shallow_copy_with_layers(entity.depth)
        new_entities = [ent for ent in self.entities if ent.depth == entity.depth]
        return GameState(False, self.player_1_iden, self.player_2_iden, new_world, new_entities)

    def view_spec(self) -> 'GameState':
        return GameState(False, self.player_1_iden, self.player_2_iden, self.world, self.entities)

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
        arr.write(self.player_1_iden.to_bytes(4, byteorder='big', signed=False))
        arr.write(self.player_2_iden.to_bytes(4, byteorder='big', signed=False))

        wserd: bytes = ser.serialize(self.world)
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
        p1_iden = int.from_bytes(arr.read(4), 'big', signed=False)
        p2_iden = int.from_bytes(arr.read(4), 'big', signed=False)
        wlen = int.from_bytes(arr.read(8), 'big', signed=False)
        world = ser.deserialize(arr.read(wlen))

        nents = int.from_bytes(arr.read(4), 'big', signed=False)
        entities = []
        for _ in range(nents):
            elen = int.from_bytes(arr.read(4), 'big', signed=False)
            ent = ser.deserialize(arr.read(elen))
            entities.append(ent)

        return cls(auth_val == 1, p1_iden, p2_iden, world, entities)

ser.register(GameState)
