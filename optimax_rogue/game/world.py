"""Describes the world, i.e., the layers (dungeons) and the tiles on them
"""

import enum
import io
import typing
import numpy as np
import optimax_rogue.networking.serializer as ser

class Tile(enum.IntEnum):
    """Describes a tile on the world as an enum. They are typically stored
    as integers rather than wrapped, but they can be more easily displayed
    with str(Tile(tile))
    """
    Ground = 1
    Wall = 2
    StaircaseDown = 3

class Dungeon(ser.Serializable):
    """Describes the map for a layer of the world. The map does not change
    throughout gameplay

    Attributes:
        tiles (np.ndarray[width x height]): the world int tuple, where each item
            corresponds to a tile.
    """

    def __init__(self, tiles: np.ndarray) -> None:
        self.tiles = tiles

    @property
    def width(self):
        """Gets how many tiles wide the map is"""
        return self.tiles.shape[0]

    @property
    def height(self):
        """Gets how many tiles tall the map is"""
        return self.tiles.shape[1]

    def is_blocked(self, x: int, y: int) -> bool: # pylint: disable=invalid-name
        """Returns True if the given tile is blocked or outside the map,
        False otherwise"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.tiles[x, y] == Tile.Wall

    @classmethod
    def has_custom_serializer(cls) -> bool:
        """Returns True to use a numpy serialization strategy"""
        return True

    def to_prims(self) -> bytes:
        """Returns a compressed representation of this dungeon"""
        arr = io.BytesIO()
        np.savez_compressed(arr, tiles=self.tiles)
        return arr.getvalue()

    @classmethod
    def from_prims(cls, prims: bytes) -> 'Dungeon':
        """Returns the uncompressed dungeon"""
        arr = io.BytesIO(prims)
        arr.seek(0, 0)
        with np.load(arr) as uncomp:
            return cls(uncomp['tiles'])

ser.register(Dungeon)

class World(ser.Serializable):
    """Describes the static components of the world, which is a collection of dungeons,
    which may be partially loaded

    Attributes:
        dungeons (dict[int, Dungeon]): a dictionary from layer to dungeon, where 0 corresponds
            to the very first layer that things spawn at
    """

    def __init__(self, dungeons: typing.Dict[int, Dungeon]) -> None:
        self.dungeons = dungeons

    def get_at_depth(self, ind: int) -> Dungeon:
        """Gets the dungeon at the specified depth"""
        return self.dungeons[ind]

    def set_at_depth(self, ind: int, dung: Dungeon) -> None:
        """Sets the dungeon at the specified depth"""
        self.dungeons[ind] = dung

    def del_at_depth(self, ind: int) -> None:
        """Deletes the dungeon at the specified depth"""
        del self.dungeons[ind]

    @classmethod
    def has_custom_serializer(cls) -> bool:
        """Returns True since this uses a custom serialization strategy"""
        return True

    def to_prims(self) -> bytes:
        """Serializes the world into bytes"""
        arr = io.BytesIO()
        arr.write(len(self.dungeons).to_bytes(4, byteorder='big', signed=False))
        for depth, dung in enumerate(self.dungeons):
            serd = dung.to_prims()
            arr.write(depth.to_bytes(4, byteorder='big', signed=False))
            arr.write(len(serd).to_bytes(8, byteorder='big', signed=False))
            arr.write(serd)
        return arr.getvalue()

    @classmethod
    def from_prims(cls, prims: bytes) -> 'World':
        """Deserializes the given serialized world"""
        arr = io.BytesIO(prims)
        arr.seek(0, 0)
        num = int.from_bytes(arr.read(4), 'big', False)
        dungeons = dict()
        for _ in range(num):
            depth = int.from_bytes(arr.read(4), 'big', False)
            size = int.from_bytes(arr.read(8), 'big', False)
            lyr = Dungeon.from_prims(arr.read(size))
            dungeons[depth] = lyr
        return cls(dungeons)

ser.register(World)